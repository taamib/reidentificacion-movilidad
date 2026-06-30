# Aplicación: tasa de enlace por grupo

import pandas as pd

from ..decision.tasa import tasa


# Calcula la tasa de enlace por grupo de un atributo
def tasa_por_grupo(enlazadas: pd.Index, atributo: pd.Series) -> pd.DataFrame:
    con_grupo = atributo.dropna()
    print(f"  {len(con_grupo):,} entidades quedaron en {con_grupo.nunique():,} grupos")

    filas = []
    for grupo, entidades in con_grupo.groupby(con_grupo):
        filas.append({
            atributo.name: grupo,
            "personas":    len(entidades),
            "tasa_enlace": tasa(enlazadas, entidades.index),
        })
    return pd.DataFrame(filas)
