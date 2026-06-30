# Capa 2: co-ocurrencias y conteo de dias de coincidencia

import numpy as np
import pandas as pd

DESPLAZAMIENTO = np.uint64(32)
MASCARA = np.uint64(0xFFFFFFFF)
TOPE_ID = int(np.iinfo("uint32").max)


# Las parejas distintas de un dia, a partir de los bloques que entrega la busqueda
def parejas_del_dia(bloques):
    trozos, n_coocurrencias = [], 0
    for bloque in bloques:
        trozos.append(bloque[["entidad_A", "entidad_B"]].drop_duplicates())
        n_coocurrencias += len(bloque)
    if not trozos:
        return pd.DataFrame(columns=["entidad_A", "entidad_B"]), 0
    parejas = pd.concat(trozos, ignore_index=True).drop_duplicates(ignore_index=True)
    return parejas, n_coocurrencias


# Las dos entidades de una pareja dentro de un mismo entero de 64 bits: A en la mitad alta, B
# en la baja. Decision de diseño para optimizar memoria y velocidad
# Exige que los identificadores quepan en 32 bits
def empaquetar(parejas):
    a = parejas["entidad_A"].to_numpy("int64")
    b = parejas["entidad_B"].to_numpy("int64")
    if len(a) and (min(a.min(), b.min()) < 0 or max(a.max(), b.max()) > TOPE_ID):
        raise ValueError(
            f"los identificadores tienen que caber en 32 bits (entre 0 y {TOPE_ID:,}). "
        )
    return (a.astype("uint64") << DESPLAZAMIENTO) | b.astype("uint64")


# En cuántos días distintos coincidio cada pareja
def contar_dias(parejas_por_dia: list) -> pd.DataFrame:
    claves = [empaquetar(dia) for dia in parejas_por_dia]
    unicas, dias = np.unique(np.concatenate(claves), return_counts=True)
    claves.clear()
    return pd.DataFrame({
        "entidad_A":     (unicas >> DESPLAZAMIENTO).astype("int64"),
        "entidad_B":     (unicas & MASCARA).astype("int64"),
        "n_dias_juntos": dias.astype("uint8"),
    })
