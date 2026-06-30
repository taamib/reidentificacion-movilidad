import numpy as np
import pandas as pd
from sklearn.neighbors import BallTree

from ..config import RADIO_METROS, VENTANA_MINUTOS

# Cada cuantos minutos se corta el día para buscar
PASO_MINUTOS = 15


# Definición 5: los días que las dos fuentes observaron. Un día que solo una de las dos vio no
# puede aportar ninguna co-ocurrencia, porque hace falta un evento de cada una.
def dias_en_comun(eventos_A: pd.DataFrame, eventos_B: pd.DataFrame) -> list:
    fecha_A = pd.to_datetime(eventos_A["timestamp"]).dt.date
    fecha_B = pd.to_datetime(eventos_B["timestamp"]).dt.date
    return sorted(set(fecha_A) & set(fecha_B))


# Las co-ocurrencias entre las dos fuentes
# La búsqueda va por bloques de PASO_MINUTOS porque el árbol solo sabe de distancia y no de tiempo
def bloques_de_candidatos(fuente_A: pd.DataFrame, fuente_B: pd.DataFrame,
                          radio_m: int = RADIO_METROS,
                          ventana_min: int = VENTANA_MINUTOS,
                          paso_minutos: int = PASO_MINUTOS,
                          contexto: bool = False):
    A = fuente_A.copy()
    B = fuente_B.copy()
    for tabla in (A, B):
        instante = pd.to_datetime(tabla["timestamp"])
        tabla["fecha"] = instante.dt.date
        tabla["minuto"] = instante.dt.hour * 60 + instante.dt.minute # En minutos para poder cortar en bloques

    radio_en_radianes = radio_m / 6_371_000
    dias = sorted(set(A["fecha"]) & set(B["fecha"]))

    for fecha in dias:
        dia_A = A[A["fecha"] == fecha]
        dia_B = B[B["fecha"] == fecha]
        if dia_A.empty or dia_B.empty:
            continue

        for desde in range(0, 24 * 60, paso_minutos):
            hasta = desde + paso_minutos
            franja_A = dia_A[dia_A["minuto"].between(desde, hasta - 1)].reset_index(drop=True)
            # Franja B se amplia +-ventana_minutos para que el arbol encuentre vecinos que esten dentro de la ventana temporal
            franja_B = dia_B[dia_B["minuto"].between(desde - ventana_min,
                                                     hasta - 1 + ventana_min)].reset_index(drop=True)
            if franja_A.empty or franja_B.empty:
                continue

            # El árbol se construye con la fuente más grande y se consulta con la más chica por eficiencia 
            consultar_A = len(franja_A) <= len(franja_B)
            datos_arbol = franja_B if consultar_A else franja_A
            datos_consulta = franja_A if consultar_A else franja_B

            arbol = BallTree(np.radians(datos_arbol[["lat", "lon"]].values), metric="haversine")

            # query_radius: para cada punto de consulta devuelve los puntos del árbol que están
            # dentro del radio, como una lista de arrays. idx_list[i] son los vecinos del punto i
            idx_list = arbol.query_radius(
                np.radians(datos_consulta[["lat", "lon"]].values), r=radio_en_radianes)

            cuantos_vecinos = np.array([len(x) for x in idx_list])
            if cuantos_vecinos.sum() == 0:
                continue

            # Aplanamos arrays de arrays. Ejemplo:
            #   idx_list   = [[2, 5], [8], []] (punto 0 -> puntos del árbol 2 y 5 etc...)
            #   cuantos    = [2, 1, 0]
            #   posicion_consulta = [0, 0, 1] repetimos el indice del punto según cuantos vecinos tiene
            #   posicion_arbol    = [2, 5, 8] vecinos aplanados
            posicion_consulta = np.repeat(np.arange(len(datos_consulta)), cuantos_vecinos)
            posicion_arbol = np.concatenate(idx_list).astype(int)
            if consultar_A:
                posicion_A, posicion_B = posicion_consulta, posicion_arbol
            else:
                posicion_A, posicion_B = posicion_arbol, posicion_consulta

            ts_A = franja_A["timestamp"].values[posicion_A]
            ts_B = franja_B["timestamp"].values[posicion_B]
            delta_min = (ts_A - ts_B) / np.timedelta64(1, "m")
            dentro_ventana = np.abs(delta_min) <= ventana_min
            if not dentro_ventana.any():
                continue

            posicion_A = posicion_A[dentro_ventana]
            posicion_B = posicion_B[dentro_ventana]

            pares = pd.DataFrame({
                "entidad_A": franja_A["entidad_id"].values[posicion_A],
                "entidad_B": franja_B["entidad_id"].values[posicion_B],
            })
            if not contexto:
                yield pares[["entidad_A", "entidad_B"]]
                continue

            pares["lat_B"] = franja_B["lat"].values[posicion_B]
            pares["lon_B"] = franja_B["lon"].values[posicion_B]
            pares["hora"] = franja_B["minuto"].values[posicion_B] // 60
            yield pares[["entidad_A", "entidad_B", "lat_B", "lon_B", "hora"]]
