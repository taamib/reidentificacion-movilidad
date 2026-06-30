# Orquestador del framework, corre las cuatro etapas 
import json
import time
from datetime import datetime
from pathlib import Path

import pandas as pd

from .config import TRABAJO, RADIO_METROS, VENTANA_MINUTOS, MIN_DIAS_COINCIDENCIA
from .enlace.espaciotemporal import bloques_de_candidatos
from .enlace.agregacion import parejas_del_dia, contar_dias
from .decision.enlace_mutuo import enlace_mutuo, entidades_enlazadas, favorita_sin_empate
from .decision.tasa import tasa
from .aplicacion.por_grupo import tasa_por_grupo


# Las parejas de un dia. Si el día ya se calculo antes se lee del disco
def procesar_dia(fecha, eventos_A, eventos_B, cache, radio_m, ventana_min):
    archivo = cache / f"parejas_{fecha}.parquet"
    if archivo.exists():
        parejas = pd.read_parquet(archivo)
        print(f"    ya estaba hecho: {len(parejas):,} parejas", flush=True)
        return parejas

    inicio = time.time()
    parejas, n_coocurrencias = parejas_del_dia(
        bloques_de_candidatos(eventos_A, eventos_B, radio_m=radio_m, ventana_min=ventana_min)
    )
    parejas.to_parquet(archivo, index=False)

    print(f"    {n_coocurrencias:,} co-ocurrencias, {len(parejas):,} parejas distintas, "
          f"{(time.time() - inicio) / 60:.1f} min", flush=True)
    return parejas


# cargar_A, cargar_B: los adaptadores
# poblacion: sobre quiénes se mide la tasa global
# atributos: función que recibe los eventos de A y devuelve un diccionario {nombre: atributo} para medir la tasa por grupo
# cache:     carpeta de  checkpoints por día
# resultados_en: dónde dejar los números finales. None por defecto
def correr(cargar_A, cargar_B, poblacion=None, atributos=None,
           min_dias=MIN_DIAS_COINCIDENCIA, radio_m=RADIO_METROS,
           ventana_min=VENTANA_MINUTOS, cache=None, resultados_en=None) -> dict:
    inicio = time.time()
    cache = Path(cache) if cache else TRABAJO / f"cache_r{radio_m}_v{ventana_min}"
    cache.mkdir(parents=True, exist_ok=True)

    print(f"Parámetros: radio={radio_m} m | ventana=±{ventana_min} min | "
          f"mínimo {min_dias} días de coincidencia", flush=True)

    print("\nCAPA 1: traduciendo cada fuente al esquema común con su adaptador...")
    eventos_A = cargar_A()
    eventos_B = cargar_B()

    fecha_A = pd.to_datetime(eventos_A["timestamp"]).dt.date
    fecha_B = pd.to_datetime(eventos_B["timestamp"]).dt.date
    dias_comunes = sorted(set(fecha_A) & set(fecha_B))
    for nombre, eventos, fecha in (("A", eventos_A, fecha_A), ("B", eventos_B, fecha_B)):
        print(f"  Fuente {nombre}: {len(eventos):>12,} eventos | "
              f"{eventos['entidad_id'].nunique():>9,} entidades | "
              f"{min(fecha)} a {max(fecha)}", flush=True)
    print(f"  Días en común a usar: {len(dias_comunes)} | "
          f"desde {min(dias_comunes)} hasta {max(dias_comunes)}", flush=True)

    print("\nCAPA 2: buscando co-ocurrencias y contando en cuántos días coincidió cada pareja...")
    parejas_por_dia = []
    for numero, fecha in enumerate(dias_comunes, start=1):
        print(f"  Día {numero}/{len(dias_comunes)}  {fecha}", flush=True)
        parejas_por_dia.append(procesar_dia(
            fecha, eventos_A[fecha_A == fecha], eventos_B[fecha_B == fecha],
            cache, radio_m, ventana_min,
        ))

    pares = contar_dias(parejas_por_dia)
    del parejas_por_dia
    # Queda en el caché junto al resto de los intermedios
    pares.to_parquet(cache / "pares.parquet", index=False, compression="zstd")
    print(f"  {len(pares):,} parejas distintas (una entidad de A con una de B), cada una con "
          f"el número de días en que coincidieron", flush=True)

    print("\nCAPA 3: decidiendo qué candidatos se aceptan como enlace...")
    # Las tres condiciones se calculan por separado para poder mostrar
    fuertes = pares[pares["n_dias_juntos"] >= min_dias]
    favoritas = favorita_sin_empate(fuertes, "entidad_A", "entidad_B")
    mutuos = enlace_mutuo(pares, min_dias=min_dias)
    enlazadas = entidades_enlazadas(pares, min_dias=min_dias)
    print(f"  De {len(pares):,} parejas candidatas:")
    print(f"    {len(fuertes):>12,}  coincidieron en {min_dias} días o más (evidencia suficiente)")
    print(f"    {len(favoritas):>12,}  donde la mejor candidata de A es única (A elige a B)")
    print(f"    {len(mutuos):>12,}  donde además B elige a A: se aceptan como enlace mutuo")

    if poblacion is None:
        poblacion = pd.Index(eventos_A["entidad_id"].unique())
    poblacion = pd.Index(poblacion)
    poblacion_activa = pd.Index(eventos_A.loc[fecha_A.isin(dias_comunes), "entidad_id"].unique())
    tasa_global = tasa(enlazadas, poblacion)
    tasa_activa = tasa(enlazadas, poblacion_activa)
    print("  Tasa de enlace, la fracción de la población que quedó enlazada:")
    print(f"    {100*tasa_global:5.2f}%  sobre las {len(poblacion):,} entidades observadas de A")
    print(f"    {100*tasa_activa:5.2f}%  sobre las {len(poblacion_activa):,} que tuvieron "
          f"actividad en los {len(dias_comunes)} días en común")

    # La misma tasa, pero dentro de cada grupo
    tablas, por_atributo = {}, {}
    for nombre, atributo in (atributos(eventos_A) if atributos else {}).items():
        print(f"\nAPLICACIÓN: agrupando por {atributo.name} y calculando la tasa de cada grupo...")
        tablas[nombre] = tasa_por_grupo(enlazadas, atributo)
        con_atributo = atributo.dropna().index
        tasa_atributo = tasa(enlazadas, con_atributo)
        # Si se aleja de la tasa global, los grupos no describen a la población sino a una
        # parte que se enlaza distinto
        print(f"  entre ellas la tasa de enlace es {100*tasa_atributo:.2f}%, "
              f"contra {100*tasa_global:.2f}% de la población completa")
        # Sin atributo no son solo las NaN: también las que nunca entraron a la Serie
        print(f"  {len(poblacion.difference(con_atributo)):,} de las {len(poblacion):,} "
              f"de la población quedaron sin {atributo.name}")
        por_atributo[atributo.name] = {"n": len(con_atributo),
                                       "tasa_enlace": round(tasa_atributo, 4)}

    if resultados_en is not None:
        embudo = {"n_pares_fuertes": len(fuertes), "n_favoritas": len(favoritas)}
        guardar_resultados(resultados_en, dias_comunes, pares, mutuos, tablas,
                           poblacion, poblacion_activa, tasa_global, tasa_activa,
                           por_atributo, embudo, min_dias, radio_m, ventana_min,
                           time.time() - inicio)

    print(f"\nTerminado en {(time.time() - inicio) / 60:.1f} min", flush=True)
    return {
        "pares":       pares,
        "mutuos":      mutuos,
        "enlazadas":   enlazadas,
        "tasa_global": tasa_global,
        "tasa_activa": tasa_activa,
        "tablas":      tablas,
    }


# Los numeros finales
def guardar_resultados(resultados_en, dias_comunes, pares, mutuos, tablas,
                       poblacion, poblacion_activa, tasa_global, tasa_activa,
                       por_atributo, embudo, min_dias, radio_m, ventana_min, segundos):
    resultados_en = Path(resultados_en)
    resultados_en.mkdir(parents=True, exist_ok=True)

    mutuos.to_parquet(resultados_en / "mutuos.parquet", index=False)
    for nombre, tabla in tablas.items():
        tabla.to_csv(resultados_en / f"{nombre}.csv", index=False)

    # Un solo archivo describe la corrida
    (resultados_en / "resumen.json").write_text(json.dumps({
        "fecha_corrida":       datetime.now().isoformat(timespec="seconds"),
        "n_poblacion":         len(poblacion),
        "n_poblacion_activa":  len(poblacion_activa),
        "n_pares":             len(pares),
        "n_pares_fuertes":     embudo["n_pares_fuertes"],
        "n_favoritas":         embudo["n_favoritas"],
        "n_enlaces":           len(mutuos),
        "tasa_enlace":         round(tasa_global, 4),
        "tasa_enlace_activa":  round(tasa_activa, 4),
        "por_atributo":        por_atributo,
        "n_dias":              len(dias_comunes),
        "fechas":              [str(f) for f in dias_comunes],
        "min_dias":            min_dias,
        "radio_m":             radio_m,
        "ventana_min":         ventana_min,
        "segundos":            round(segundos, 1),
    }, indent=2, ensure_ascii=False))

    print("\nGuardado:")
    print(f"  {resultados_en}/resumen.json     los números de esta corrida")
    print(f"  {resultados_en}/mutuos.parquet   los {len(mutuos):,} enlaces aceptados")
    for nombre in tablas:
        print(f"  {resultados_en}/{nombre}.csv  la tasa por grupo")
