# Capa 3: regla de decisión 
#
# Recibe los pares con en cuántos días coincidieron y decide cuáles se aceptan como enlace:
# evidencia suficiente, favorita sin empate, y elección reciproca

import pandas as pd

from ..config import MIN_DIAS_COINCIDENCIA


# Elegir la candidata con más días de coincidencia, siempre que sea única  
def favorita_sin_empate(pares: pd.DataFrame, clave: str, elegido: str) -> pd.DataFrame:
    maximos = pares.groupby(clave)["n_dias_juntos"].transform("max")
    topes = pares[pares["n_dias_juntos"] == maximos]
    cuantos_en_tope = topes.groupby(clave)[elegido].transform("size")
    return topes[cuantos_en_tope == 1]


# Un par se acepta solo si las dos entidades se eligen entre sí
def enlace_mutuo(pares: pd.DataFrame, min_dias: int = MIN_DIAS_COINCIDENCIA) -> pd.DataFrame:
    fuertes = pares[pares["n_dias_juntos"] >= min_dias]

    elige_A = favorita_sin_empate(fuertes, "entidad_A", "entidad_B")
    elige_B = favorita_sin_empate(fuertes, "entidad_B", "entidad_A")

    mutuos = elige_A.merge(elige_B[["entidad_A", "entidad_B"]],
                           on=["entidad_A", "entidad_B"], how="inner")
    return mutuos[["entidad_A", "entidad_B", "n_dias_juntos"]].reset_index(drop=True)


# Las entidades de A que quedaron en algún enlace. Es lo que recibe tasa()
def entidades_enlazadas(pares: pd.DataFrame, min_dias: int = MIN_DIAS_COINCIDENCIA) -> pd.Index:
    return pd.Index(enlace_mutuo(pares, min_dias)["entidad_A"].unique())
