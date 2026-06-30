# Los numeros que el generador sintetico necesita, medidos sobre las fuentes reales para usar como base

import json
from datetime import datetime

import numpy as np
import pandas as pd

from reid.config import RES_VALIDACION
from reid.fuentes.bip import cargar_eventos as cargar_bip
from reid.fuentes.cdr import cargar_eventos as cargar_cdr

SALIDA = RES_VALIDACION / "anclaje.json"


MIN_DIAS_ACTIVOS = 3      # días mínimos para verle una rutina a una tarjeta
LUGARES_FREC = 3          # lugares frecuentes que se le miden a cada tarjeta
VENTANA_RUTINA_MIN = 90   # ancho alrededor del bloque horario dominante
USUARIOS_RITMO = 5000    # muestra para medir los huecos entre pings

# Resumen estadístico de la serie
def resumen(serie: pd.Series) -> dict:
    q = serie.quantile([0.01, 0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95, 0.99, 0.995, 0.999])
    return {
        "n": int(serie.size),
        "media": round(float(serie.mean()), 2),
        "cv": round(float(serie.std() / serie.mean()), 3),
        "min": float(serie.min()),
        "max": float(serie.max()),
        "percentiles": {f"p{p*100:g}": round(float(v), 2) for p, v in q.items()},
    }


# Conteo de cada valor de la serie hasta un tope
def conteo(serie: pd.Series, tope: int = 60) -> dict:
    hasta_tope = serie[serie < tope].value_counts().sort_index()
    tabla = {str(int(valor)): int(n) for valor, n in hasta_tope.items()}
    tabla[f"{tope}+"] = int((serie >= tope).sum())
    return tabla


def solo_rutina_dominante(eventos: pd.DataFrame, grupo: str) -> pd.DataFrame:
    con_bloque = eventos.assign(bloque=(eventos["minuto"] // 30) * 30)  # agregar columna de bloques horarios de media hora
    veces = con_bloque.groupby([grupo, "bloque"]).size().rename("n").reset_index()
    pico_por_grupo = (veces.sort_values(["n", "bloque"], ascending=[False, True])
                      .drop_duplicates(grupo).set_index(grupo)["bloque"])

    pico = eventos[grupo].map(pico_por_grupo)
    return eventos[(eventos["minuto"] - pico).abs() <= VENTANA_RUTINA_MIN]


### Dónde

# Cuantos paraderos hay y como se reparten los eventos y tarjetas en ellos
def paraderos(bip: pd.DataFrame) -> dict:
    tarjetas = bip.groupby(["lat", "lon"])["entidad_id"].nunique()
    return {
        "n_paraderos": int(len(tarjetas)),
        "eventos_por_paradero": resumen(bip.groupby(["lat", "lon"]).size()),
        "tarjetas_por_paradero": resumen(tarjetas),
    }

# Cuantos paraderos visita cada entidad  y como se distribuyen
def lugares_por_persona(bip: pd.DataFrame) -> dict:
    n = bip.groupby(["entidad_id", "lat", "lon"]).size().groupby(level=0).size()
    return {"distribucion": resumen(n), "conteo": conteo(n)}


#### Cuanto se mueve cada persona 

 # Cuantas validaciones deja cada tarjeta en la semana
def actividad_por_persona(bip: pd.DataFrame) -> dict:
    n = bip.groupby("entidad_id").size()
    return {"distribucion": resumen(n), "conteo": conteo(n)}


 # De los lugares frecuentes de una persona, en qué fracción de los días se ve cada uno
def visitas_por_rango(bip: pd.DataFrame, n_dias: int) -> dict:
    por_lugar = bip.groupby(["entidad_id", "lat", "lon"]).size().rename("n").reset_index()
    dias = bip.groupby("entidad_id")["fecha"].nunique()
    n_lugares = por_lugar.groupby("entidad_id").size().reindex(dias.index, fill_value=0)
    validas = dias[(dias >= MIN_DIAS_ACTIVOS) & (n_lugares >= LUGARES_FREC)].index

    top = (por_lugar[por_lugar["entidad_id"].isin(validas)]
           .sort_values(["entidad_id", "n"], ascending=[True, False])
           .groupby("entidad_id").head(LUGARES_FREC).copy())
    top["rango"] = top.groupby("entidad_id").cumcount() + 1

    con_rango = bip.merge(top[["entidad_id", "lat", "lon", "rango"]],
                          on=["entidad_id", "lat", "lon"], how="inner")
    dias_por_rango = con_rango.groupby(["entidad_id", "rango"])["fecha"].nunique()
    mediana = (dias_por_rango / n_dias).groupby("rango").median()
    return {
        "n_tarjetas": int(len(validas)),
        "prob_diaria_por_rango": {str(int(r)): round(float(v), 3) for r, v in mediana.items()},
    }


### Cuando 

# Cuanto se reparten las horas de personas distintas en un mismo paradero concurrido
def dispersion_entre_personas(bip: pd.DataFrame, n_paraderos: int = 20) -> dict:
    populares = (bip.groupby(["lat", "lon"])["entidad_id"].nunique()
                 .sort_values(ascending=False).head(n_paraderos)
                 .reset_index()[["lat", "lon"]])
    en_populares = bip.merge(populares, on=["lat", "lon"], how="inner")
    en_populares["paradero"] = list(zip(en_populares["lat"], en_populares["lon"]))
    rutina = solo_rutina_dominante(en_populares, "paradero")
    por_paradero = rutina.groupby("paradero")["minuto"].std()
    return {
        "n_paraderos": int(n_paraderos),
        "dispersion_min": round(float(por_paradero.median()), 1),
    }

# Cuanto varía una misma tarjeta de un día a otro, en su paradero habitual
def variacion_por_persona(bip: pd.DataFrame) -> dict:
    por_lugar = bip.groupby(["entidad_id", "lat", "lon"]).size().rename("n").reset_index()
    habitual = por_lugar.loc[por_lugar.groupby("entidad_id")["n"].idxmax()]
    en_habitual = bip.merge(habitual[["entidad_id", "lat", "lon"]],
                            on=["entidad_id", "lat", "lon"], how="inner")
    rutina = solo_rutina_dominante(en_habitual, "entidad_id")

    dias = rutina.groupby("entidad_id")["fecha"].nunique()
    validas = dias[dias >= MIN_DIAS_ACTIVOS].index
    por_tarjeta = rutina[rutina["entidad_id"].isin(validas)].groupby("entidad_id")["minuto"].std()
    return {
        "n_tarjetas": int(len(validas)),
        "variacion_min": round(float(por_tarjeta.median()), 1),
    }


# A que hora del dia se usa un paradero concurrido. De aca sale el horario habitual que el
# generador le da a cada persona en cada uno de sus lugares
def perfil_horario(bip: pd.DataFrame, n_paraderos: int = 20) -> dict:
    populares = (bip.groupby(["lat", "lon"])["entidad_id"].nunique()
                 .sort_values(ascending=False).head(n_paraderos)
                 .reset_index()[["lat", "lon"]])
    en_populares = bip.merge(populares, on=["lat", "lon"], how="inner")
    por_hora = en_populares.groupby(en_populares["minuto"] // 60).size()
    return {
        "n_paraderos": int(n_paraderos),
        "n_eventos": int(len(en_populares)),
        "pct_por_hora": {int(h): round(100 * n / len(en_populares), 1)
                         for h, n in por_hora.items()},
    }


### Lo que ve el CDR 
# Cada cuánto pingea un celular
def ritmo_pings(cdr: pd.DataFrame, semilla: int = 0) -> dict:
    rng = np.random.default_rng(semilla)
    usuarios = cdr["entidad_id"].unique()
    muestra = rng.choice(usuarios, min(USUARIOS_RITMO, len(usuarios)), replace=False)
    sub = cdr[cdr["entidad_id"].isin(muestra)].sort_values(["entidad_id", "timestamp"])
    huecos = sub.groupby(["entidad_id", "fecha"])["timestamp"].diff().dt.total_seconds() / 60

    por_dia = sub.groupby(["entidad_id", "fecha"]).size()

    return {
        "pings_por_dia": resumen(por_dia),
        "hueco_entre_pings_min": resumen(huecos.dropna()),
        "n_usuarios_muestra_huecos": int(len(muestra)),
    }



# En que horas del dia ocurren los pings
def horas_activas(cdr: pd.DataFrame) -> dict:
    por_hora = cdr.groupby(cdr["minuto"] // 60).size()
    return {
        "primera_hora_con_pings": int(por_hora.index.min()),
        "ultima_hora_con_pings": int(por_hora.index.max()),
        "pct_entre_6_y_24": round(100 * por_hora.loc[6:23].sum() / por_hora.sum(), 2),
        "pct_por_hora": {int(h): round(100 * n / por_hora.sum(), 2) for h, n in por_hora.items()},
    }


# Que fracción de los momentos del día de una persona tiene un ping cerca
def cobertura_temporal(cdr: pd.DataFrame, ventana_min: int = 3, semilla: int = 0) -> dict:
    rng = np.random.default_rng(semilla)
    usuarios = cdr["entidad_id"].unique()
    muestra = rng.choice(usuarios, min(2_000, len(usuarios)), replace=False)
    sub = cdr[cdr["entidad_id"].isin(muestra)].sort_values(["entidad_id", "timestamp"])

    cubiertos = total = 0
    for _, dia in sub.groupby(["entidad_id", "fecha"]):
        t = np.sort(dia["timestamp"].to_numpy("datetime64[s]").astype("int64"))
        inicio = int(pd.Timestamp(dia["fecha"].iloc[0]).timestamp()) + 6 * 3600
        instantes = inicio + rng.integers(0, 18 * 3600, 20)
        i = np.searchsorted(t, instantes) # posicion donde cae cada instante en la lista de pings ordenada
        antes = np.where(i > 0, instantes - t[np.clip(i - 1, 0, len(t) - 1)], 10**9)
        despues = np.where(i < len(t), t[np.clip(i, 0, len(t) - 1)] - instantes, 10**9)
        cubiertos += int((np.minimum(antes, despues) <= ventana_min * 60).sum())
        total += len(instantes)

    return {
        "ventana_min": ventana_min,
        "fraccion_cubierta": round(cubiertos / total, 3),
        "n_instantes": int(total),
    }


def preparar(eventos: pd.DataFrame) -> pd.DataFrame:
    eventos = eventos.copy()
    instante = pd.to_datetime(eventos["timestamp"])
    eventos["fecha"] = instante.dt.date
    eventos["minuto"] = instante.dt.hour * 60 + instante.dt.minute
    return eventos


# Corre en orden una lista de mediciones sobre una fuente, avisando por donde va
def medir_cada_una(mediciones: list, fuente) -> dict:
    resultado = {}
    for nombre, calcular in mediciones:
        print(f"midiendo {nombre}...", flush=True)
        resultado[nombre] = calcular(fuente)
    return resultado


# Lo que se mide sobre el Bip
def medir_bip() -> dict:
    print("Cargando Bip...", flush=True)
    bip = preparar(cargar_bip())
    n_dias = bip["fecha"].nunique()
    print(f"  {len(bip):,} eventos | {bip['entidad_id'].nunique():,} tarjetas | {n_dias} dias\n")

    return {"n_eventos": len(bip),
            "n_tarjetas": int(bip["entidad_id"].nunique()),
            "n_dias": int(n_dias),
            **medir_cada_una([
                ("paraderos", paraderos),
                ("lugares_por_persona", lugares_por_persona),
                ("actividad_por_persona", actividad_por_persona),
                ("visitas_por_rango", lambda b: visitas_por_rango(b, n_dias)),
                ("dispersion_entre_personas", dispersion_entre_personas),
                ("perfil_horario", perfil_horario),
                ("variacion_por_persona", variacion_por_persona),
            ], bip)}


# Lo que se mide sobre el CDR
def medir_cdr() -> dict:
    print("\nCargando CDR...", flush=True)
    cdr = preparar(cargar_cdr())
    print(f"  {len(cdr):,} pings | {cdr['entidad_id'].nunique():,} usuarios\n")

    return {"n_eventos": len(cdr),
            "n_usuarios": int(cdr["entidad_id"].nunique()),
            **medir_cada_una([
                ("ritmo_pings", ritmo_pings),
                ("horas_activas", horas_activas),
                ("cobertura_temporal", cobertura_temporal),
            ], cdr)}


# Mide todo sobre las dos fuentes reales y escribe anclaje.json
def medir() -> None:
    medido = {
        "corrida": {"fecha": datetime.now().isoformat(timespec="seconds"),
                    "ventana_rutina_min": VENTANA_RUTINA_MIN,
                    "min_dias_activos": MIN_DIAS_ACTIVOS},
        "bip": medir_bip(),
        "cdr": medir_cdr(),
    }

    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    SALIDA.write_text(json.dumps(medido, indent=2, ensure_ascii=False))
    print(f"\nGuardado en {SALIDA}")
