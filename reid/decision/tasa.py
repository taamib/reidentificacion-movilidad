# Capa 3: tasa de enlace
import pandas as pd


# enlazadas / poblacion 
def tasa(enlazadas: pd.Index, poblacion: pd.Index) -> float:
    enlazadas = pd.Index(enlazadas).unique()
    poblacion = pd.Index(poblacion).unique()

    if len(poblacion) == 0:
        raise ValueError("la tasa de enlace no está definida sobre una población vacía")

    return len(poblacion.intersection(enlazadas)) / len(poblacion)
