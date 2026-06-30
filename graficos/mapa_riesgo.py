# Mapa de la tasa de enlace por comuna

import pandas as pd
import matplotlib.pyplot as plt
from reid.config import FIGURAS, RES_CASO
from reid.config_caso import MIN_ENTIDADES_GRUPO
from reid.aplicacion.hogar import cargar_comunas_rm


def main():
    tabla = pd.read_csv(RES_CASO / "tasa_comuna.csv")
    tabla = tabla[tabla["personas"] >= MIN_ENTIDADES_GRUPO].copy()

    comunas = cargar_comunas_rm()
    geo = comunas.merge(tabla, on="comuna_gadm", how="inner")

    fig, ax = plt.subplots(1, 1, figsize=(8, 8))

    geo.plot(
        ax=ax,
        column="tasa_enlace",
        cmap="OrRd",
        edgecolor="white",
        linewidth=0.5,
        legend=True,
        legend_kwds={
            "label": "Fracción bruta de usuarios enlazados",
            "orientation": "horizontal",
            "fraction": 0.03,
            "pad": 0.02,
            "format": "{x:.0%}",
        },
    )

    # Solo se etiquetan las comunas con área suficiente para que quepa el nombre
    for _, row in geo.iterrows():
        if row.geometry.area > 0.002:
            c = row.geometry.centroid
            ax.annotate(row["comuna_gadm"], xy=(c.x, c.y), ha="center", va="center",
                        fontsize=6, color="#222222")

    minx, miny, maxx, maxy = geo.total_bounds
    m = 0.03
    ax.set_xlim(minx - m, maxx + m)
    ax.set_ylim(miny - m, maxy + m)

    ax.set_title(f"Fracción bruta de usuarios enlazados\n"
                 f"Comunas con al menos {MIN_ENTIDADES_GRUPO} usuarios CDR", fontsize=12, pad=12)
    ax.set_axis_off()

    plt.tight_layout()
    out = FIGURAS / "mapa_riesgo_comuna.png"
    fig.savefig(out, dpi=200, bbox_inches="tight")
    print(f"Guardado en {out}")
    plt.close()


if __name__ == "__main__":
    main()
