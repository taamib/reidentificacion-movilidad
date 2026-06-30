# Mapa de los agrupamientos locales (LISA) de la tasa de enlace por comuna 

import json
import pandas as pd
import matplotlib.pyplot as plt

from reid.config import FIGURAS, RES_CASO
from reid.aplicacion.hogar import cargar_comunas_rm


COLORES = {
    "Alto-Alto":        "#c0392b",
    "Bajo-Alto":        "#7fb3d5",
    "Bajo-Bajo":        "#2c6fbb",
    "Alto-Bajo":        "#f1948a",
    "No significativo": "#e6e6e6",
}


def main():
    moran = json.loads((RES_CASO / "moran_comuna.json").read_text())
    lisa = pd.read_csv(RES_CASO / "lisa_comuna.csv")

    geo = cargar_comunas_rm().merge(lisa, on="comuna_gadm", how="inner")

    fig, ax = plt.subplots(1, 1, figsize=(8, 8))
    geo.plot(ax=ax, color=[COLORES[c] for c in geo["cluster"]],
             edgecolor="white", linewidth=0.5)
    for etiqueta, color in COLORES.items():
        ax.scatter([], [], color=color, label=etiqueta)
    ax.legend(loc="upper right", fontsize=9, title="Agrupamiento local")
    ax.set_title(f"Agrupamientos locales de la tasa bruta de enlace (LISA)\n"
                 f"Comunas con al menos {moran['min_usuarios']} usuarios CDR\n"
                 f"Moran's I = {moran['moran_I']:+.2f}, p = {moran['p_sim']:.3f}",
                 fontsize=12, pad=12)
    ax.set_axis_off()
    plt.tight_layout()

    out = FIGURAS / "moran_lisa_riesgo.png"
    fig.savefig(out, dpi=200, bbox_inches="tight")
    print(f"Guardado en {out}")
    plt.close()


if __name__ == "__main__":
    main()
