# Cuan concentrada esta la demanda del Bip entre sus paraderos
#
# Una co-ocurrencia en un paradero muy concurrido distingue poco, porque por ahi pasa
# demasiada gente. Esta figura muestra cuanta demanda cabe en cuan pocos paraderos.

import json

import matplotlib.pyplot as plt
import numpy as np

from reid.config import FIGURAS, RES_CASO


def main():
    c = json.loads((RES_CASO / "descripcion_fuentes.json").read_text())["concentracion_bip"]
    x = 100 * np.array(c["lorenz_x"])
    y = 100 * np.array(c["lorenz_y"])

    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.plot(x, y, linewidth=2, color="#c0392b")
    ax.plot([0, 100], [0, 100], linestyle=":", linewidth=1, color="#888888",
            label="reparto parejo")

    for objetivo, color in (("0.5", "#2c6fbb"), ("0.8", "#555555")):
        h = c["hitos"][objetivo]
        px, py = 100 * h["frac_paraderos"], 100 * float(objetivo)
        ax.plot([px, px, 0], [0, py, py], linestyle="--", linewidth=1, color=color, alpha=0.8)
        ax.annotate(f"{h['paraderos']:,} paraderos ({px:.1f}%)\nconcentran el {py:.0f}%",
                    xy=(px + 3, py - 9), fontsize=9, color=color)

    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.set_xlabel("Paraderos, del más concurrido al menos concurrido (%)")
    ax.set_ylabel("Validaciones acumuladas (%)")
    ax.set_title("La demanda del Bip se concentra en muy pocos paraderos")
    ax.legend(frameon=False, loc="lower right")
    ax.grid(True, alpha=0.3)
    plt.tight_layout()

    out = FIGURAS / "concentracion_bip.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    print(f"Guardado en {out}")
    plt.close()


if __name__ == "__main__":
    main()
