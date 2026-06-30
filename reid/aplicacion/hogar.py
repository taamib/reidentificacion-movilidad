import pandas as pd
import geopandas as gpd
from shapely.geometry import Point

from ..config_caso import COMUNAS_GEOJSON

# Un grado de longitud cubre menos terreno que uno de latitud, en Santiago cubre un 83%
FACTOR_LON = 0.83

# Estima el hogar de cada usuario a partir de sus pings nocturnos
def estimar_hogar(cdr: pd.DataFrame) -> pd.DataFrame:
    hora = pd.to_datetime(cdr["timestamp"]).dt.hour
    pings_noche = cdr[(hora >= 22) | (hora < 7)].copy()
    print(f"  Pings nocturnos: {len(pings_noche):,} de {len(cdr):,} total ({100*len(pings_noche)/len(cdr):.1f}%)")

    # Mediana por usuario, repetida en cada uno de sus pings, para medir distancias
    mediana = pings_noche.groupby("entidad_id")[["lat", "lon"]].transform("median")
    dist2 = ((pings_noche["lat"] - mediana["lat"]) ** 2
             + ((pings_noche["lon"] - mediana["lon"]) * FACTOR_LON) ** 2)

    # El medoid es el ping que está más cerca de la mediana, por usuario
    idx_medoide = dist2.groupby(pings_noche["entidad_id"]).idxmin()
    hogar = (
        pings_noche.loc[idx_medoide, ["entidad_id", "lat", "lon"]]
        .rename(columns={"lat": "lat_hogar", "lon": "lon_hogar"})
        .reset_index(drop=True)
    )
    print(f"  Usuarios con hogar estimado: {len(hogar):,}")
    return hogar

def cargar_comunas_rm() -> gpd.GeoDataFrame:
    print("  Cargando comunas de GADM...")
    comunas = gpd.read_file(COMUNAS_GEOJSON)
    comunas_rm = comunas[comunas["NAME_1"] == "SantiagoMetropolitan"].copy()
    comunas_rm = comunas_rm[["NAME_3", "geometry"]].rename(columns={"NAME_3": "comuna_gadm"})
    comunas_rm = comunas_rm.set_crs("EPSG:4326", allow_override=True)
    print(f"  Comunas RM cargadas: {len(comunas_rm)}")
    return comunas_rm.reset_index(drop=True)

# A que comuna cae el hogar de cada usuario
def asignar_comuna(hogar: pd.DataFrame, comunas_rm: gpd.GeoDataFrame) -> pd.DataFrame:
    if hogar["entidad_id"].duplicated().any():
        raise ValueError("La tabla de hogares debe contener una fila por entidad_id")

    geometria = [Point(lon, lat) for lat, lon in zip(hogar["lat_hogar"], hogar["lon_hogar"])]
    hogar_geo = gpd.GeoDataFrame(hogar.copy(), geometry=geometria, crs="EPSG:4326")

    cruce = gpd.sjoin(hogar_geo, comunas_rm, how="left", predicate="within")
    asignadas = cruce.dropna(subset=["comuna_gadm"])
    n_comunas = asignadas.groupby("entidad_id")["comuna_gadm"].nunique()
    ids_ambiguos = n_comunas[n_comunas > 1].index

    asignacion_unica = (
        asignadas[~asignadas["entidad_id"].isin(ids_ambiguos)]
        [["entidad_id", "comuna_gadm"]]
        .drop_duplicates(subset="entidad_id")
        .set_index("entidad_id")["comuna_gadm"]
    )
    resultado = hogar.copy()
    resultado["comuna_gadm"] = resultado["entidad_id"].map(asignacion_unica)

    n_asignados = resultado["comuna_gadm"].notna().sum()
    n_total = len(resultado)
    print(f"  Usuarios con comuna asignada: {n_asignados:,} / {n_total:,} ({100*n_asignados/n_total:.1f}%)")
    print(f"  Usuarios con asignación ambigua excluidos: {len(ids_ambiguos):,}")
    return resultado
