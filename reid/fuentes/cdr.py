# Adaptador del caso de estudio (CDR de Santiago)
import glob
import pandas as pd
from pathlib import Path

from ..config_caso import (
    TELEFONIA,
    MIN_PINGS_DIA,
    RM_FRACCION_MIN,
    LAT_MIN_RM, LAT_MAX_RM,
    LON_MIN_RM, LON_MAX_RM,
)

from .esquema import a_eventos


def procesar_cdr(path=None) -> pd.DataFrame:
    if path is None:
        path = TELEFONIA

    archivos = sorted(glob.glob(str(Path(path) / "*.parquet")))
    print(f"Archivos CDR encontrados: {len(archivos)}")

    filtrados = []

    for archivo in archivos:
        df_archivo = pd.read_parquet(archivo)

        dentro_rm = (
            df_archivo["lat"].between(LAT_MIN_RM, LAT_MAX_RM) &
            df_archivo["lon"].between(LON_MIN_RM, LON_MAX_RM)
        )

        # Para cada usuario, calcular la fracción de pings que están en la RM
        df_archivo["en_rm"] = dentro_rm
        fraccion_en_rm_por_usuario = df_archivo.groupby("user_id")["en_rm"].mean()

        # Quedarse solo con los usuarios que tengan +80% pings en RM
        usuarios_de_rm = fraccion_en_rm_por_usuario[fraccion_en_rm_por_usuario >= RM_FRACCION_MIN].index
        df_filtrado = df_archivo[df_archivo["user_id"].isin(usuarios_de_rm)].copy()
        df_filtrado = df_filtrado.drop(columns=["en_rm"])

        filtrados.append(df_filtrado)

    df = pd.concat(filtrados, ignore_index=True)
    print(f"Registros tras carga inicial: {len(df):,}")
    print(f"Usuarios tras carga inicial: {df['user_id'].nunique():,}")
    print(f"Usuarios tras filtro fracción RM (>={RM_FRACCION_MIN*100:.0f}%): {df['user_id'].nunique():,}")

    # Filtrar por días con al menos 5 pings
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df["fecha"] = df["timestamp"].dt.date

    pings_por_usuario_dia = df.groupby(["user_id", "fecha"]).size().reset_index(name="n_pings")

    dias_validos = pings_por_usuario_dia[pings_por_usuario_dia["n_pings"] >= MIN_PINGS_DIA]
    dias_validos = dias_validos[["user_id", "fecha"]]

    df = df.merge(dias_validos, on=["user_id", "fecha"], how="inner")

    print(f"Usuarios tras filtro días (>={MIN_PINGS_DIA} pings/día): {df['user_id'].nunique():,}")
    print(f"Registros finales: {len(df):,}")

    return df


def cargar_eventos() -> pd.DataFrame:
    cdrs = procesar_cdr()
    df = a_eventos(
        cdrs,
        fuente="cdr",
        col_entidad="user_id",
        col_lat="lat",
        col_lon="lon",
        col_timestamp="timestamp",
    )
    return df

