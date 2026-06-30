# Tasa de enlace segun cuantos datos hay de cada persona

import json
import pandas as pd
from scipy import stats

from reid.config import RES_CASO
from reid.fuentes.cdr import cargar_eventos as cargar_cdr
from reid.aplicacion.atributos import atributo_cuartil_actividad, actividad_mediana_por_cuartil
from reid.aplicacion.por_grupo import tasa_por_grupo

# Esto devuelve entre que valores puede moverse (al 95%), y es
# lo que permite decir que los cuartiles son distintos entre si 
def wilson(k, n, z=1.96):
    p = k / n
    centro = (p + z*z/(2*n)) / (1 + z*z/n)
    medio = z * ((p*(1-p)/n + z*z/(4*n*n)) ** 0.5) / (1 + z*z/n)
    return centro - medio, centro + medio


def main():
    # La misma fuente que usa el pipeline, para contar sobre los mismos eventos
    eventos = cargar_cdr()

    # Leemos resultados guardados de la capa 3, enlaces mutuos
    mutuos = pd.read_parquet(RES_CASO / "mutuos.parquet", columns=["entidad_A"])
    enlazadas = pd.Index(mutuos["entidad_A"].unique())

    cuartil = atributo_cuartil_actividad(eventos)
    tabla = tasa_por_grupo(enlazadas, cuartil)
    tabla = tabla.merge(actividad_mediana_por_cuartil(eventos, cuartil).reset_index(),
                        on="cuartil")

    limites = [wilson(round(t * n), n) for t, n in zip(tabla["tasa_enlace"], tabla["personas"])]
    tabla["ic_bajo"] = [lo for lo, _ in limites]
    tabla["ic_alto"] = [hi for _, hi in limites]

    print(tabla.to_string(index=False))

    RES_CASO.mkdir(parents=True, exist_ok=True)
    tabla.to_csv(RES_CASO / "tasa_actividad.csv", index=False)

    # Correlacion pings vs enlazado, a nivel de persona
    actividad = eventos["entidad_id"].value_counts()
    r, p = stats.spearmanr(actividad.values, actividad.index.isin(enlazadas).astype(int))
    print(f"\nSpearman pings vs enlazado: r = {r:+.2f}  p = {p:.1e}")
    (RES_CASO / "spearman_actividad.json").write_text(json.dumps({
        "r": round(float(r), 3), "p": float(p), "n": int(len(actividad)),
    }, indent=2, ensure_ascii=False))

    print(f"\nGuardado en {RES_CASO / 'tasa_actividad.csv'} y {RES_CASO / 'spearman_actividad.json'}")


if __name__ == "__main__":
    main()
