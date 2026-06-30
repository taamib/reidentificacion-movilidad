# Tasa de enlace por cuartil de actividad

import pandas as pd
import matplotlib.pyplot as plt

from reid.config import FIGURAS, RES_CASO


ETIQUETAS = ["Q1\n(menor actividad)", "Q2", "Q3", "Q4\n(mayor actividad)"]


def main():
    tabla = pd.read_csv(RES_CASO / "tasa_actividad.csv")

    alturas = tabla["tasa_enlace"] * 100
    bajo = tabla["ic_bajo"] * 100
    alto = tabla["ic_alto"] * 100

    fig, ax = plt.subplots(figsize=(6, 4.5))
    ax.bar(ETIQUETAS, alturas, color="#c0392b", alpha=0.85,
           yerr=[alturas - bajo, alto - alturas], capsize=5,
           error_kw={"ecolor": "#333333", "elinewidth": 1.2})
    for i, (valor, tope) in enumerate(zip(alturas, alto)):
        ax.text(i, tope + 0.2, f"{valor:.1f}%", ha="center", fontsize=10)

    ax.set_ylabel("Tasa bruta de enlace (%)")
    ax.set_xlabel("Cuartil de actividad en el CDR (número de pings)")
    ax.set_title("La tasa bruta de enlace aumenta con la actividad observada")
    ax.grid(True, axis="y", alpha=0.3)
    plt.tight_layout()

    out = FIGURAS / "riesgo_por_actividad.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    print(f"Guardado en {out}")
    plt.close()


if __name__ == "__main__":
    main()
