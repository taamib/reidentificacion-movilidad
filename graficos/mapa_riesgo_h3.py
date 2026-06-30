# Mapa de la tasa de enlace en hexagonos H3, con las comunas de la RM de fondo

import json
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt

from reid.config import FIGURAS, RES_CASO
from reid.aplicacion.atributos import poligono_h3
from reid.aplicacion.hogar import cargar_comunas_rm


def main():
    moran = json.loads((RES_CASO / "moran_h3.json").read_text())
    celda = pd.read_csv(RES_CASO / "tasa_h3.csv")


    geo = gpd.GeoDataFrame(celda, geometry=[poligono_h3(c) for c in celda["h3"]], crs="EPSG:4326")
    comunas = cargar_comunas_rm()

    fig, ax = plt.subplots(1, 1, figsize=(8, 8))
    comunas.plot(ax=ax, color="none", edgecolor="#cccccc", linewidth=0.6)
    geo.plot(ax=ax, column="tasa_enlace", cmap="OrRd", edgecolor="white", linewidth=0.2,
             legend=True, legend_kwds={"label": "Fracción bruta de usuarios enlazados",
                                       "orientation": "horizontal", "fraction": 0.03,
                                       "pad": 0.02, "format": "{x:.0%}"})
    minx, miny, maxx, maxy = comunas.total_bounds
    m = 0.03
    ax.set_xlim(minx - m, maxx + m)
    ax.set_ylim(miny - m, maxy + m)
    ax.set_title(f"Fracción bruta de enlace en hexágonos H3\nRegión Metropolitana\n"
                 f"Moran's I = {moran['moran_I']:+.2f}, p = {moran['p_sim']:.3f}",
                 fontsize=12, pad=12)
    ax.set_axis_off()
    plt.tight_layout()

    out = FIGURAS / "mapa_riesgo_h3.png"
    fig.savefig(out, dpi=200, bbox_inches="tight")
    print(f"Guardado en {out}")
    plt.close()


if __name__ == "__main__":
    main()
