# Donde puede observar el Bip
#
# Los paraderos del diccionario sobre las comunas de la Region Metropolitana. La red cubre
# el nucleo urbano y deja fuera la periferia, que es lo que dice la tabla de cobertura.

import geopandas as gpd
import matplotlib.pyplot as plt
from shapely.geometry import Point

from reid.config import FIGURAS
from reid.fuentes.paraderos import cargar_diccionario
from reid.aplicacion.hogar import cargar_comunas_rm


def main():
    dic = cargar_diccionario().drop_duplicates(subset=["lat", "lon"])
    com = cargar_comunas_rm()
    paraderos = gpd.GeoDataFrame(
        dic, geometry=[Point(lo, la) for la, lo in zip(dic.lat, dic.lon)], crs="EPSG:4326")

    # Solo los que caen dentro de la region, para que el mapa no se estire
    dentro = gpd.sjoin(paraderos, com, how="inner", predicate="within")
    dentro = dentro.drop_duplicates(subset=["lat", "lon"])

    fig, ax = plt.subplots(figsize=(7, 7))
    com.boundary.plot(ax=ax, color="#999999", linewidth=0.6)
    dentro.plot(ax=ax, color="#c0392b", markersize=1.4, alpha=0.65)

    ax.set_title(f"Los {len(dentro):,} paraderos del diccionario en la Región Metropolitana"
                 .replace(",", "."))
    ax.set_axis_off()
    plt.tight_layout()

    out = FIGURAS / "red_bip.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    print(f"Guardado en {out}")
    plt.close()


if __name__ == "__main__":
    main()
