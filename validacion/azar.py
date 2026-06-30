# Cuantos enlaces produce el azar

import numpy as np
import pandas as pd

from reid.config import RADIO_METROS, VENTANA_MINUTOS
from reid.decision.enlace_mutuo import enlace_mutuo
from reid.enlace.agregacion import contar_dias
from reid.enlace.espaciotemporal import bloques_de_candidatos
from validacion.enlace import separar_por_dia

# Grupo donde se barajan las identidades de B
GRUPO_AZAR = ["lat_B", "lon_B", "hora"]


# Las co-ocurrencias de cada dia, con el contexto que hace falta para armar los grupos
def candidatos_por_dia(eventos_A: pd.DataFrame, eventos_B: pd.DataFrame,
                       radio_m: int = RADIO_METROS,
                       ventana_min: int = VENTANA_MINUTOS) -> list[pd.DataFrame]:
    por_dia = []
    for dia_A, dia_B in separar_por_dia(eventos_A, eventos_B):
        bloques = list(bloques_de_candidatos(dia_A, dia_B, radio_m=radio_m,
                                             ventana_min=ventana_min, contexto=True))
        if bloques:
            por_dia.append(pd.concat(bloques, ignore_index=True))
    return por_dia


# En cuantos dias distintos coincidio cada pareja. Sin ningun dia no hay nada que contar
def contar_dias_de(parejas_por_dia: list[pd.DataFrame]) -> pd.DataFrame:
    if not parejas_por_dia:
        return pd.DataFrame(columns=["entidad_A", "entidad_B", "n_dias_juntos"])
    return contar_dias(parejas_por_dia)


# Los pares tal como salen
def pares_observados(candidatos: list[pd.DataFrame]) -> pd.DataFrame:
    return contar_dias_de([c[["entidad_A", "entidad_B"]].drop_duplicates(ignore_index=True)
                           for c in candidatos])


# Las parejas de un dia con las identidades de B permutadas dentro de cada grupo
def barajar_dia(candidatos: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    # Guarda el numero que se le asigna a cada grupo y la identidad de B 
    parejas = pd.DataFrame({
        "grupo": candidatos.groupby(GRUPO_AZAR, sort=False).ngroup().to_numpy(),
        "entidad_B": candidatos["entidad_B"].to_numpy(),
    })

    unicas = parejas.drop_duplicates().sort_values("grupo").reset_index(drop=True)
    orden = np.lexsort((rng.random(len(unicas)), unicas["grupo"].to_numpy()))
    unicas["nueva"] = unicas["entidad_B"].to_numpy()[orden]

    # Tabla final con la identidad de B permutada dentro de cada grupo
    nueva = parejas.merge(unicas, on=["grupo", "entidad_B"], how="left")["nueva"]

    return pd.DataFrame({"entidad_A": candidatos["entidad_A"].to_numpy(),
                         "entidad_B": nueva.to_numpy()}).drop_duplicates(ignore_index=True)


# Los pares de una barajada completa del periodo, con en cuantos dias coincidio cada uno
def pares_de_una_baraja(candidatos: list[pd.DataFrame],
                        rng: np.random.Generator) -> pd.DataFrame:
    return contar_dias_de([barajar_dia(dia, rng) for dia in candidatos])


# Cuantos enlaces deja cada barajada, para cada umbral de dias
def enlaces_del_azar(candidatos: list, umbrales: list[int], n_repeticiones: int,
                     rng: np.random.Generator) -> dict[int, list[int]]:
    conteos = {umbral: [] for umbral in umbrales}
    for i in range(n_repeticiones):
        baraja = pares_de_una_baraja(candidatos, rng)
        for umbral in umbrales:
            conteos[umbral].append(len(enlace_mutuo(baraja, min_dias=umbral)))
        del baraja
        # Solo cuando son muchas: una corrida larga necesita saber por donde va
        if n_repeticiones >= 20:
            print(f"    barajada {i + 1}/{n_repeticiones}", flush=True)
    return conteos


# El test del azar de punta a punta sobre dos fuentes cualquiera
def test_de_azar(eventos_A: pd.DataFrame, eventos_B: pd.DataFrame,
                 umbrales: list[int], n_barajadas: int = 30,
                 radio_m: int = RADIO_METROS, ventana_min: int = VENTANA_MINUTOS,
                 semilla: int = 0) -> pd.DataFrame:
    print(f"Buscando co-ocurrencias a {radio_m} m y {ventana_min} min...", flush=True)
    candidatos = candidatos_por_dia(eventos_A, eventos_B, radio_m=radio_m, ventana_min=ventana_min)
    observados = pares_observados(candidatos)
    print(f"  {sum(len(c) for c in candidatos):,} co-ocurrencias | "
          f"{len(observados):,} parejas distintas", flush=True)

    print(f"Barajando {n_barajadas} veces...", flush=True)
    conteos = enlaces_del_azar(candidatos, umbrales, n_barajadas, np.random.default_rng(semilla))
    del candidatos

    filas = []
    for umbral in umbrales:
        real = len(enlace_mutuo(observados, min_dias=umbral))
        azar = np.array(conteos[umbral], dtype=float)
        filas.append({"umbral_dias": umbral, "real": real,
                      "azar_media": azar.mean(), "azar_std": azar.std(),
                      "exceso": real - azar.mean(),
                      "pct_explicado_azar": 100 * azar.mean() / real if real else float("nan"),
                      # Ninguna barajada llega al observado -> el minimo posible, 1/(n+1)
                      "p_valor_monte_carlo": (1 + (azar >= real).sum()) / (len(azar) + 1),
                      "n_shuffles": n_barajadas,
                      "radio_m": radio_m, "ventana_min": ventana_min})
        f = filas[-1]
        print(f"  {umbral} dias: real {real:,} | azar {f['azar_media']:.1f} +-{f['azar_std']:.1f} "
              f"| exceso {f['exceso']:.1f} | el azar explica el {f['pct_explicado_azar']:.1f}%",
              flush=True)

    return pd.DataFrame(filas)
