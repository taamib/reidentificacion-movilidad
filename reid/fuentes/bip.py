# Adaptador del caso de estudio (Bip de Santiago)
import os
import glob
import pandas as pd

from ..config_caso import VIAJES, VIAJES_BIP, COLUMNAS_VIAJES_ELIMINAR
from .paraderos import cargar_diccionario, normalizar
from .esquema import a_eventos

# Los .csv.gz originales son lentos de leer, así que se convierten una vez a parquet y de
# paso se les pega la coordenada del paradero.
def convertir_gz_a_parquet() -> None:
    os.makedirs(VIAJES_BIP, exist_ok=True)

    paraderos = cargar_diccionario()

    paraderos_subida = paraderos.rename(columns={
        "paradero": "sub_norm",
        "lat": "lat_subida",
        "lon": "lon_subida",
    })
    paraderos_bajada = paraderos.rename(columns={
        "paradero": "baj_norm",
        "lat": "lat_bajada",
        "lon": "lon_bajada",
    })

    archivos = sorted(glob.glob(str(VIAJES / "*.viajes.csv.gz")))
    print(f"Archivos a convertir: {len(archivos)}")

    for archivo in archivos:
        fecha = os.path.basename(archivo)[:10]
        archivo_salida = VIAJES_BIP / f"{fecha}.parquet"

        if archivo_salida.exists():
            print(f"  {fecha}: ya existe, saltando")
            continue

        print(f"  Convirtiendo {fecha}...")

        df = pd.read_csv(archivo, compression="gzip", sep="|")
        print(f"    Filas leídas: {len(df):,}")

        columnas_a_eliminar = [col for col in COLUMNAS_VIAJES_ELIMINAR if col in df.columns]
        df = df.drop(columns=columnas_a_eliminar)

        df["sub_norm"] = df["paradero_subida_1"].apply(normalizar)
        df["baj_norm"] = df["paradero_bajada_1"].apply(normalizar)

        df = df.merge(paraderos_subida, on="sub_norm", how="left")

        df = df.merge(paraderos_bajada, on="baj_norm", how="left")

        df = df.drop(columns=["sub_norm", "baj_norm"])

        df.to_parquet(archivo_salida, index=False, engine="pyarrow")

        pct_con_coords = df["lat_subida"].notna().mean() * 100
        print(f"    Guardado. Subida con coords: {pct_con_coords:.1f}%")

    print("Conversión completa.")


def cargar_eventos() -> pd.DataFrame:
    archivos = sorted(glob.glob(str(VIAJES_BIP / "*.parquet")))
    if not archivos:
        raise FileNotFoundError(
            f"no hay viajes convertidos en {VIAJES_BIP}. "
        )
    print(f"Archivos Bip encontrados: {len(archivos)}")

    trozos = []
    for archivo in archivos:
        dia = pd.read_parquet(
            archivo,
            columns=["id_tarjeta", "lat_subida", "lon_subida", "tiempo_subida_1"],
        )
        trozos.append(dia)

    viajes = pd.concat(trozos, ignore_index=True)
    print(f"Viajes leídos: {len(viajes):,}")
    print(f"Tarjetas distintas: {viajes['id_tarjeta'].nunique():,}")

    eventos = a_eventos(
        viajes,
        fuente="bip",
        col_entidad="id_tarjeta",
        col_lat="lat_subida",
        col_lon="lon_subida",
        col_timestamp="tiempo_subida_1",
    )

    print(f"Eventos finales con coordenadas y fecha: {len(eventos):,}")
    return eventos

