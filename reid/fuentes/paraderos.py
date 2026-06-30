# Construcción del diccionario de paraderos
#
# Datos Bip identifican los paraderos con códigos tipo L-26-12-30-PO
# o con nombres de estación de metro, pero no traen coordenadas directas.
# Este módulo arma un diccionario que traduce cada paradero a su lat/lon.
#
# Fuentes que combinamos:
#   1. DTPM (buses): trae coordenadas en UTM -> hay que convertirlas a lat/lon
#   2. GTFS (metro y tren): ya trae coordenadas en lat/lon

import pandas as pd
from pyproj import Transformer
import unicodedata
from ..config_caso import DTPM, DTPM_HOJA, PARADEROS, STOPS, TRIPS, STOP_TIMES

# Las líneas ferroviarias del GTFS que aceptan Bip: Metro (L1 a L6) y Metrotren (MTN hacia
# Nos, MTR hacia Rancagua)
lineas_ferroviarias = ["L1", "L2", "L3", "L4", "L4A", "L5", "L6", "MTN", "MTR"]

# Mapeo de nombres en los datos Bip que no coinciden con GTFS
aliases = {
    "CAL Y CANTO"           : "PUENTE CAL Y CANTO",
    "PARQUE OHIGGINS"       : "PARQUE O'HIGGINS",
    "RONDIZONNI"            : "RONDIZZONI",
    "PLAZA MAIPU"           : "PLAZA DE MAIPU",
    "ESTACION ALAMEDA"      : "ESTACION CENTRAL",
    "UNION LATINO AMERICANA": "UNION LATINOAMERICANA",
}

# Mayúsculas y sin tildes
def normalizar(texto: str) -> str:
    texto = str(texto).upper().strip()
    texto = unicodedata.normalize("NFD", texto)
    return "".join(c for c in texto if unicodedata.category(c) != "Mn")

def cargar_buses() -> pd.DataFrame:
    paraderos = pd.read_excel(DTPM, sheet_name=DTPM_HOJA)

    # El Excel del DTPM no trae encabezados limpios
    paraderos.columns = [
        "orden", "codigo_ts", "codigo_usuario", "sentido", "variante", "un",
        "codigo_paradero", "codigo_paradero_usuario", "comuna", "eje",
        "desde", "hacia", "x", "y", "nombre", "zona_paga", "excepciones",
    ]
    # x e y vienen en UTM
    paraderos["x"] = pd.to_numeric(paraderos["x"], errors="coerce")
    paraderos["y"] = pd.to_numeric(paraderos["y"], errors="coerce")
    paraderos = paraderos.dropna(subset=["x", "y", "codigo_paradero"]).copy()

    transformer = Transformer.from_crs("EPSG:32719", "EPSG:4326", always_xy=True)
    lon, lat = transformer.transform(paraderos["x"].values, paraderos["y"].values)
    paraderos["lat"] = lat
    paraderos["lon"] = lon
   
    return (
        paraderos.groupby("codigo_paradero")
        .first()[["lat", "lon"]]
        .reset_index()
        .rename(columns={"codigo_paradero": "paradero"})
    )

def cargar_metro() -> pd.DataFrame:
    trips = pd.read_csv(TRIPS)
    stop_times = pd.read_csv(STOP_TIMES)
    stops = pd.read_csv(STOPS)

    trips_metro = trips[trips["route_id"].isin(lineas_ferroviarias)]
    stops_metro = stop_times[stop_times["trip_id"].isin(trips_metro["trip_id"])]
    stop_times_metro = stops_metro.merge(
        stops[["stop_id", "stop_name", "stop_lat", "stop_lon"]], on="stop_id"
    )
    # Una estación aparece muchas veces (un registro por viaje), dejamos una por stop_id
    stop_times_metro = (
        stop_times_metro[["stop_id", "stop_name", "stop_lat", "stop_lon"]]
        .drop_duplicates("stop_id")
        .copy()
    )

    # Recortamos el nombre del paradero a lo que viene antes de "Dirección" o "(Anden"
    stop_times_metro["paradero"] = (
        stop_times_metro["stop_name"]
        .str.split(r"[Dd]irecci", regex=True).str[0]   # corta antes de "Dirección"
        .str.split(r"\(Anden",    regex=True).str[0]   # corta antes de "(Anden"
        .str.strip()
        .apply(normalizar)
    )

    return (
        stop_times_metro[["paradero", "stop_lat", "stop_lon", "stop_name"]]
        .rename(columns={"stop_lat": "lat", "stop_lon": "lon", "stop_name": "nombre"})
        .drop_duplicates("paradero")
    )

def cargar_aliases(df: pd.DataFrame) -> pd.DataFrame:
    coords = df.set_index("paradero")
    filas = []
    for alias, original in aliases.items():
        # Solo agregamos el alias si su estación real está en el diccionario de metro
        if original in coords.index:
            lat, lon = coords.loc[original, ["lat", "lon"]]
            filas.append({"paradero": alias, "lat": lat, "lon": lon, "nombre": original})
    return pd.DataFrame(filas)

def construir_diccionario(guardar: bool = True) -> pd.DataFrame:
    paraderos_buses = cargar_buses()
    paraderos_metro = cargar_metro()
    df_aliases      = cargar_aliases(paraderos_metro)

    diccionario = pd.concat(
        [paraderos_buses, paraderos_metro, df_aliases], ignore_index=True
    ).drop_duplicates("paradero")

    if guardar:
        diccionario.to_csv(PARADEROS, index=False)

    return diccionario


def cargar_diccionario() -> pd.DataFrame:
    return pd.read_csv(PARADEROS)[["paradero", "lat", "lon"]].drop_duplicates("paradero")
