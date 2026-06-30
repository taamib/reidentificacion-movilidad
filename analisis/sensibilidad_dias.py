# Cuantos usuarios quedan enlazados usando solo los primeros dias del Bip

import json

import pandas as pd

from reid.config import (TRABAJO, RES_CASO, RES_VALIDACION,
                         RADIO_METROS, VENTANA_MINUTOS, MIN_DIAS_COINCIDENCIA)
from reid.decision.enlace_mutuo import entidades_enlazadas
from reid.enlace.agregacion import contar_dias


# Las parejas de cada dia que dejo el pipeline, en orden de fecha
def parejas_por_dia(radio_m: int, ventana_min: int) -> list[pd.DataFrame]:
    cache = TRABAJO / f"cache_r{radio_m}_v{ventana_min}"
    archivos = sorted(cache.glob("parejas_*.parquet"))
    if not archivos:
        raise SystemExit(f"no hay parejas en {cache}: corre primero 'python correr.py caso'")
    return [pd.read_parquet(a) for a in archivos]


def main() -> None:
    poblacion = json.loads((RES_CASO / "resumen.json").read_text())["n_poblacion"]
    dias = parejas_por_dia(RADIO_METROS, VENTANA_MINUTOS)
    print(f"{len(dias)} dias en el cache | poblacion de {poblacion:,} usuarios CDR", flush=True)

    filas = []
    # Con menos dias que el umbral de coincidencia no puede haber ningun enlace
    for k in range(MIN_DIAS_COINCIDENCIA, len(dias) + 1):
        enlazadas = entidades_enlazadas(contar_dias(dias[:k]), min_dias=MIN_DIAS_COINCIDENCIA)
        pct = 100 * len(enlazadas) / poblacion
        filas.append({"dias_usados": k, "n_enlazados": len(enlazadas), "pct_enlazados": pct,
                      "radio_m": RADIO_METROS, "ventana_min": VENTANA_MINUTOS,
                      "min_dias": MIN_DIAS_COINCIDENCIA})
        print(f"  {k} dias: {len(enlazadas):,} enlazados ({pct:.2f}%)", flush=True)

    salida = RES_VALIDACION / "sensibilidad_dias.csv"
    pd.DataFrame(filas).to_csv(salida, index=False)
    print(f"Guardado en {salida}")


if __name__ == "__main__":
    main()
