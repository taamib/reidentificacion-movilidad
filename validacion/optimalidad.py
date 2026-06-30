# Elegir el radio, la ventana y el minimo de dias optimos
# Para casos sinteticos hay verdad y se puede observar metricas, pero para caso real solo se puede mirar exceso sobre azar

import time
from itertools import product
from pathlib import Path

import numpy as np
import pandas as pd

from reid.decision.enlace_mutuo import enlace_mutuo
from validacion.azar import candidatos_por_dia, enlaces_del_azar, pares_observados
from validacion.metricas import evaluar

RADIOS = [200, 300, 400, 500, 600]
VENTANAS = [1, 2, 3, 5]
UMBRALES = [2, 3, 4, 5]
N_REPETICIONES = 10

PARAMETROS = ["radio_m", "ventana_min", "min_dias"]


# La mitad de las entidades de una fuente
def mitad(eventos: pd.DataFrame, lado: int, semilla: int = 0) -> pd.DataFrame:
    entidades = np.sort(eventos["entidad_id"].unique())
    a_la_primera = np.random.default_rng(semilla).random(len(entidades)) < 0.5
    elegidas = entidades[a_la_primera if lado == 1 else ~a_la_primera]
    return eventos[eventos["entidad_id"].isin(elegidas)].reset_index(drop=True)


# Una fila por combinacion de los tres parametros
def correr(eventos_A: pd.DataFrame, eventos_B: pd.DataFrame,
           verdad: pd.DataFrame | None = None,
           radios: list[int] = RADIOS, ventanas: list[int] = VENTANAS,
           umbrales: list[int] = UMBRALES,
           n_repeticiones: int = N_REPETICIONES, semilla: int = 0,
           guardar_en: Path | None = None) -> pd.DataFrame:
    rng = np.random.default_rng(semilla)
    filas = []

    # De la combinacion mas barata a la mas cara
    combinaciones = sorted(product(radios, ventanas), key=lambda rv: rv[0] ** 2 * rv[1])

    for radio, ventana in combinaciones:
        inicio = time.time()
        candidatos = candidatos_por_dia(eventos_A, eventos_B, radio_m=radio, ventana_min=ventana)
        observados = pares_observados(candidatos)
        del_azar = enlaces_del_azar(candidatos, umbrales, n_repeticiones, rng)
        del candidatos

        for umbral in umbrales:
            mutuos = enlace_mutuo(observados, min_dias=umbral)
            azar = del_azar[umbral]
            fila = {"radio_m": radio, "ventana_min": ventana, "min_dias": umbral,
                    "observados": len(mutuos),
                    "azar": float(np.mean(azar)),
                    "azar_std": float(np.std(azar)),
                    "exceso": len(mutuos) - float(np.mean(azar)),
                    "n_repeticiones": n_repeticiones}
            if verdad is not None:
                fila |= evaluar(mutuos, verdad)
            filas.append(fila)

        print(f"  radio={radio:>4} ventana={ventana:>2}  [{time.time() - inicio:.0f}s]", flush=True)
        if guardar_en is not None:
            pd.DataFrame(filas).to_csv(guardar_en, index=False)

    return pd.DataFrame(filas)


# Que combinacion elige cada criterio
def resumen(tabla: pd.DataFrame, titulo: str) -> None:
    gana_azar = tabla.loc[tabla["exceso"].idxmax()]
    print(f"\n{titulo}")
    print(f"  el exceso sobre el azar elige {gana_azar[PARAMETROS].to_dict()}, "
          f"con {gana_azar.exceso:.1f} enlaces de exceso sobre {gana_azar.observados:.0f}")
    if "f1" in tabla.columns:
        gana_f1 = tabla.loc[tabla["f1"].idxmax()]
        print(f"  el F1, que si mira la verdad, elige {gana_f1[PARAMETROS].to_dict()}, "
              f"con F1 {gana_f1.f1:.4f}")
        print(f"  la combinacion que eligio el azar tiene F1 {gana_azar.f1:.4f}")


# Una fila por criterio con la combinacion que gano, para no tener que buscarla a mano entre las
# ciento y tantas que se probaron
def elegidos(tabla: pd.DataFrame) -> pd.DataFrame:
    grupos = tabla.groupby("mitad") if "mitad" in tabla.columns else [(None, tabla)]
    filas = []
    for mitad, g in grupos:
        filas.append({"mitad": mitad, "criterio": "exceso sobre el azar",
                      **g.loc[g["exceso"].idxmax(), PARAMETROS].to_dict(),
                      "exceso": g["exceso"].max()})
        if "f1" in g.columns:
            filas.append({"mitad": mitad, "criterio": "F1 contra la verdad",
                          **g.loc[g["f1"].idxmax(), PARAMETROS].to_dict(),
                          "f1": g["f1"].max()})
    return pd.DataFrame(filas)


# Lo que eligio cada criterio, sobre la tabla completa
def resumir(tabla: pd.DataFrame) -> None:
    if "mitad" not in tabla.columns:
        resumen(tabla, "Resultado")
        return

    elegidas = []
    for lado, g in tabla.groupby("mitad"):
        resumen(g, f"Mitad {lado}")
        elegidas.append(tuple(g.loc[g["exceso"].idxmax(), PARAMETROS]))
    print(f"\nLas dos mitades eligen lo mismo: {'SI' if elegidas[0] == elegidas[1] else 'NO'}")


# La calibracion completa sobre dos fuentes sin verdad conocida
# Se parte la poblacion de A en dos mitades sin ninguna entidad en comun, se elige en una y se comprueba en la otra
def calibrar(eventos_A: pd.DataFrame, eventos_B: pd.DataFrame,
             guardar_parciales_en=None, **grilla) -> pd.DataFrame:
    partes = []
    for lado in (1, 2):
        A = mitad(eventos_A, lado)
        print(f"\nMitad {lado}: {A['entidad_id'].nunique():,} entidades de A | "
              f"{len(A):,} eventos | B completa {len(eventos_B):,}", flush=True)
        parcial = None if guardar_parciales_en is None else \
            guardar_parciales_en / f"optimalidad_mitad{lado}_parcial.csv"
        partes.append(correr(A, eventos_B, guardar_en=parcial, **grilla).assign(mitad=lado))
        del A

    return pd.concat(partes, ignore_index=True)
