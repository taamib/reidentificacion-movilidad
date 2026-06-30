# Caso de estudio: re-identificacion entre el CDR y el Bip de Santiago
#
#   python correr.py             el caso, los analisis y las figuras
#   python correr.py caso        solo el framework sobre las dos fuentes
#   python correr.py analisis    solo los numeros que el pipeline no produce
#   python correr.py figuras     solo dibujar, leyendo de resultados/caso/
#   python correr.py datos       prepara los datos crudos del Bip

import sys
import time

from reid import pipeline
from reid.config import TRABAJO, RES_CASO
from reid.aplicacion.atributos import atributo_comuna
from reid.aplicacion.hogar import estimar_hogar
from reid.fuentes.cdr import cargar_eventos as cargar_cdr
from reid.fuentes.bip import cargar_eventos as cargar_bip, convertir_gz_a_parquet
from reid.fuentes.paraderos import construir_diccionario

from analisis import cobertura_penetracion, moran_riesgo, riesgo_actividad, riesgo_h3
from graficos import cobertura_penetracion as fig_cobertura
from graficos import mapa_riesgo, mapa_riesgo_h3
from graficos import moran_riesgo as fig_moran
from graficos import riesgo_actividad as fig_actividad


# Atributo territorial del caso: comuna
def atributos_del_caso(eventos_cdr):
    hogar = estimar_hogar(eventos_cdr)
    TRABAJO.mkdir(parents=True, exist_ok=True)
    hogar.to_parquet(TRABAJO / "hogar_coords.parquet", index=False)
    return {"tasa_comuna": atributo_comuna(hogar)}


# Prepara los datos crudos del Bip
def datos():
    diccionario = construir_diccionario(guardar=True)
    print(f"Paraderos guardados: {len(diccionario):,}")
    convertir_gz_a_parquet()


def caso():
    pipeline.correr(
        cargar_A=cargar_cdr,
        cargar_B=cargar_bip,
        atributos=atributos_del_caso,
        resultados_en=RES_CASO,
    )


def analisis():
    riesgo_actividad.main()
    moran_riesgo.main()
    riesgo_h3.main()
    cobertura_penetracion.main()


def figuras():
    mapa_riesgo.main()
    mapa_riesgo_h3.main()
    fig_moran.main()
    fig_actividad.main()
    fig_cobertura.main()


ETAPAS = {"datos": datos, "caso": caso, "analisis": analisis, "figuras": figuras}
POR_DEFECTO = ["caso", "analisis", "figuras"]


def main():
    pedidas = sys.argv[1:] or POR_DEFECTO
    for nombre in pedidas:
        if nombre not in ETAPAS:
            sys.exit(f"no existe la etapa '{nombre}'. Las que hay: {', '.join(ETAPAS)}")

    inicio = time.time()
    for nombre in pedidas:
        print(f"\n{'=' * 70}\n{nombre.upper()}\n{'=' * 70}", flush=True)
        ETAPAS[nombre]()
    print(f"\nListo: {', '.join(pedidas)} en {(time.time() - inicio) / 60:.1f} min")


if __name__ == "__main__":
    main()
