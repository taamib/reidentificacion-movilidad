# Precisión, recall y F1 de un enlace contra la verdad conocida

import math

import pandas as pd


def evaluar(enlaces: pd.DataFrame, verdad: pd.DataFrame) -> dict:
    predichos = set(zip(enlaces["entidad_A"], enlaces["entidad_B"]))
    verdaderos = set(zip(verdad["entidad_A"], verdad["entidad_B"]))
    aciertos = len(predichos & verdaderos)

    precision = aciertos / len(predichos) if predichos else math.nan
    recall = aciertos / len(verdaderos) if verdaderos else math.nan
    f1 = 2 * precision * recall / (precision + recall) if aciertos else 0.0

    return {
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "aciertos": aciertos,
        "predichos": len(predichos),
        "verdaderos": len(verdaderos),
    }
