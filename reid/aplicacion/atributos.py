# Los atributos del caso de estudio

import h3
import pandas as pd
from shapely.geometry import Polygon

from .hogar import cargar_comunas_rm, asignar_comuna

RESOLUCION_H3 = 7   # ~5 km2 por hexagono (una comuna tiene decenas)


# Recibe la tabla que devuelve estimar_hogar y le busca la comuna que contiene cada hogar.
def atributo_comuna(hogar: pd.DataFrame) -> pd.Series:
    hogar = asignar_comuna(hogar, cargar_comunas_rm())
    return hogar.set_index("entidad_id")["comuna_gadm"].rename("comuna_gadm")


# Atributo territorial que asigna a cada hogar la celda H3 que lo contiene 
def atributo_h3(hogar: pd.DataFrame, resolucion: int = RESOLUCION_H3) -> pd.Series:
    celdas = [h3.latlng_to_cell(la, lo, resolucion)
              for la, lo in zip(hogar["lat_hogar"], hogar["lon_hogar"])]
    return pd.Series(celdas, index=hogar["entidad_id"], name="h3")


# La geometria de un hexagono no hay que guardarla, el codigo H3 la reconstruye
def poligono_h3(celda: str) -> Polygon:
    return Polygon([(lon, lat) for lat, lon in h3.cell_to_boundary(celda)])


# Atributo de actividad que asigna a cada usuario el cuartil de actividad en que cae
def atributo_cuartil_actividad(eventos_A: pd.DataFrame, n_cuartiles: int = 4) -> pd.Series:
    actividad = eventos_A["entidad_id"].value_counts()
    cuartiles = pd.qcut(actividad, n_cuartiles, labels=False, duplicates="drop") + 1
    return cuartiles.rename("cuartil")


# Atributo de actividad que calcula la mediana de pings por cuartil de actividad
def actividad_mediana_por_cuartil(eventos_A: pd.DataFrame, cuartil: pd.Series) -> pd.Series:
    actividad = eventos_A["entidad_id"].value_counts()
    return actividad.groupby(cuartil).median().rename("actividad_mediana")
