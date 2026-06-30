# Verdad conocida a partir de una fuente real, partiendola en dos
import numpy as np
import pandas as pd

COLUMNAS = ["entidad_id", "lat", "lon", "timestamp", "fuente"]

# Cuanto se le suma al identificador de B. El esquema comun exige enteros de 32 bits, y las dos
# mitades tienen que usar codigos distintos para la misma persona
DESPLAZAMIENTO_B = 1 << 24


# Los primeros n dias de una fuente. El CDR cubre noviembre entero pero el Bip solo la primera semana
def primeros_dias(eventos: pd.DataFrame, n_dias: int) -> pd.DataFrame:
    fecha = pd.to_datetime(eventos["timestamp"]).dt.date
    elegidos = sorted(set(fecha))[:n_dias]
    return eventos[fecha.isin(elegidos)].reset_index(drop=True)


# Partir los eventos de una fuente en dos mitades al azar, con seudonimos distintos para cada mitad
def partir_en_dos(eventos: pd.DataFrame, seed: int = 0) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    rng = np.random.default_rng(seed)

    a_la_A = rng.random(len(eventos)) < 0.5

    mitades = {}
    for lado, mascara in (("A", a_la_A), ("B", ~a_la_A)):
        mitad = eventos.loc[mascara, ["entidad_id", "lat", "lon", "timestamp"]].copy()
        mitad["fuente"] = lado
        mitades[lado] = mitad

    # Solo las personas que quedaron con eventos en las dos mitades pueden enlazarse.
    comunes = np.array(sorted(set(mitades["A"]["entidad_id"]) & set(mitades["B"]["entidad_id"])))
    verdad = pd.DataFrame({"entidad_A": comunes, "entidad_B": comunes + DESPLAZAMIENTO_B})

    mitades["B"]["entidad_id"] = mitades["B"]["entidad_id"] + DESPLAZAMIENTO_B

    return (mitades["A"][COLUMNAS].reset_index(drop=True),
            mitades["B"][COLUMNAS].reset_index(drop=True),
            verdad)
