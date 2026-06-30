# Correr la capa 2 del framework sobre dos tablas de eventos que ya están en memoria
import pandas as pd

from reid.config import RADIO_METROS, VENTANA_MINUTOS
from reid.enlace.espaciotemporal import bloques_de_candidatos, dias_en_comun
from reid.enlace.agregacion import parejas_del_dia, contar_dias


# Los eventos de cada dia en comun, ya separados. Es la forma comoda de recorrerlos.
def separar_por_dia(eventos_A: pd.DataFrame, eventos_B: pd.DataFrame) -> list[tuple]:
    fecha_A = pd.to_datetime(eventos_A["timestamp"]).dt.date
    fecha_B = pd.to_datetime(eventos_B["timestamp"]).dt.date
    return [(eventos_A[fecha_A == dia], eventos_B[fecha_B == dia])
            for dia in dias_en_comun(eventos_A, eventos_B)]


def enlazar(eventos_A: pd.DataFrame, eventos_B: pd.DataFrame,
            radio_m: int = RADIO_METROS,
            ventana_min: int = VENTANA_MINUTOS) -> pd.DataFrame:
    parejas = [parejas_del_dia(bloques_de_candidatos(
                   dia_A, dia_B, radio_m=radio_m, ventana_min=ventana_min))[0]
               for dia_A, dia_B in separar_por_dia(eventos_A, eventos_B)]
    if not parejas:
        return pd.DataFrame(columns=["entidad_A", "entidad_B", "n_dias_juntos"])
    return contar_dias(parejas)
