# Tasa de enlace en hexagonos H3 (mucho mas chicos que una comuna)
# Evalua si el patron comunal se mantiene al cambiar la unidad espacial (MAUP)

import json
import numpy as np
import pandas as pd
import geopandas as gpd
from libpysal.weights import Queen
from esda.moran import Moran

from reid.config import TRABAJO, RES_CASO
from reid.aplicacion.atributos import RESOLUCION_H3, atributo_h3, poligono_h3
from reid.aplicacion.hogar import cargar_comunas_rm, asignar_comuna
from reid.aplicacion.por_grupo import tasa_por_grupo


MIN_USUARIOS = 50   # hexagonos con menos usuarios dan una tasa poco confiable
# El resultado depende mucho de MIN_USUARIOS, asi que se recorre un rango
UMBRALES = [20, 30, 50, 80, 100]



# Moran sobre los hexagonos que superan un minimo de usuarios
def moran_con_umbral(tabla, minimo):
    c = tabla[tabla["personas"] >= minimo].reset_index(drop=True)
    g = gpd.GeoDataFrame(c, geometry=[poligono_h3(x) for x in c["h3"]], crs="EPSG:4326")
    islas = list(Queen.from_dataframe(g, use_index=False).islands)
    g_moran = g.drop(index=islas).reset_index(drop=True)
    w = Queen.from_dataframe(g_moran, use_index=False)
    w.transform = "r"
    np.random.seed(0)
    return g, g_moran, Moran(g_moran["tasa_enlace"].values, w, permutations=999), islas


def main():
    hogar = pd.read_parquet(TRABAJO / "hogar_coords.parquet")
    n_hogares_total = len(hogar)
    hogar = asignar_comuna(hogar, cargar_comunas_rm())
    hogar = hogar.dropna(subset=["comuna_gadm"]).copy()
    print(f"Hogares en la RM y con asignación comunal única: {len(hogar):,} / {n_hogares_total:,}")

    mutuos = pd.read_parquet(RES_CASO / "mutuos.parquet", columns=["entidad_A"])
    enlazadas = pd.Index(mutuos["entidad_A"].unique())

    todas = tasa_por_grupo(enlazadas, atributo_h3(hogar))

    # Sensibilidad a MIN_USUARIOS
    filas = []
    for minimo in UMBRALES:
        g, g_moran, mi_u, islas = moran_con_umbral(todas, minimo)
        filas.append({
            "min_usuarios": minimo,
            "n_hexagonos": len(g),
            "n_en_moran": len(g_moran),
            "moran_I": round(float(mi_u.I), 3),
            "p_sim": round(float(mi_u.p_sim), 3),
            "significativo": bool(mi_u.p_sim < 0.05),
        })
    sensibilidad = pd.DataFrame(filas)
    print("\nSensibilidad del agrupamiento al minimo de usuarios por hexagono:")
    print(sensibilidad.to_string(index=False))

    celda, geo_moran, mi, islas = moran_con_umbral(todas, MIN_USUARIOS)
    print(f"\nHexagonos con >= {MIN_USUARIOS} usuarios: {len(celda)}")
    print(f"Tasa por hexagono: min {celda['tasa_enlace'].min():.1%}, "
          f"mediana {celda['tasa_enlace'].median():.1%}, max {celda['tasa_enlace'].max():.1%}")
    print(f"\nMoran's I (hexagonos H3, minimo {MIN_USUARIOS}): I = {mi.I:+.3f}  p = {mi.p_sim:.3f}")
    print(f"  Celdas en el mapa: {len(celda)} | en Moran: {len(geo_moran)} | aisladas: {len(islas)}")
    print("  " + ("la tasa sigue agrupada a escala fina" if mi.I > 0 and mi.p_sim < 0.05
                  else "no hay agrupamiento claro a escala fina con este umbral"))

    RES_CASO.mkdir(parents=True, exist_ok=True)
    (RES_CASO / "moran_h3.json").write_text(json.dumps({
        "moran_I": round(float(mi.I), 3), "p_sim": round(float(mi.p_sim), 3),
        "n_hexagonos_mapa": int(len(celda)), "n_hexagonos_moran": int(len(geo_moran)),
        "n_hexagonos_aislados": int(len(islas)), "resolucion_h3": RESOLUCION_H3,
        "min_usuarios": MIN_USUARIOS,
        "n_hogares_rm_asignacion_unica": int(len(hogar)),
        "n_hogares_excluidos": int(n_hogares_total - len(hogar)),
        "escala": "hexagono_h3",
    }, indent=2, ensure_ascii=False))

    sensibilidad.to_csv(RES_CASO / "sensibilidad_h3.csv", index=False)
    celda[["h3", "personas", "tasa_enlace"]].to_csv(RES_CASO / "tasa_h3.csv", index=False)
    print(f"\nGuardado en {RES_CASO / 'moran_h3.json'}, {RES_CASO / 'sensibilidad_h3.csv'} "
          f"y {RES_CASO / 'tasa_h3.csv'}")


if __name__ == "__main__":
    main()
