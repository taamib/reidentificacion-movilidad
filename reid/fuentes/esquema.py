# El formato común de eventos
#
#   entidad_id   quién en esa fuente
#   lat, lon     dónde
#   timestamp    cuándo
#   fuente       de qué fuente viene 

import pandas as pd

COLUMNAS = ["entidad_id", "lat", "lon", "timestamp", "fuente"]

def a_eventos(
    df: pd.DataFrame,
    fuente: str,
    col_entidad: str,
    col_lat: str,
    col_lon: str,
    col_timestamp: str,
) -> pd.DataFrame:
    # Recibe la tabla cruda de una fuente y la deja en el esquema canónico
    eventos = pd.DataFrame({
        "entidad_id": df[col_entidad].values,
        "lat":        pd.to_numeric(df[col_lat], errors="coerce").values,
        "lon":        pd.to_numeric(df[col_lon], errors="coerce").values,
        "timestamp":  pd.to_datetime(df[col_timestamp], errors="coerce").values,
        "fuente":     fuente,
    })

    antes = len(eventos)
    eventos = eventos.dropna(subset=["lat", "lon", "timestamp"]).reset_index(drop=True)
    descartados = antes - len(eventos)
    if descartados > 0:
        print(f"  {fuente}: {descartados:,} eventos sin coordenadas o sin fecha, descartados")

    return eventos[COLUMNAS]
