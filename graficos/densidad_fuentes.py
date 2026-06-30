# Cuantos eventos deja cada entidad en un dia, en las dos fuentes
#
# Muestra la asimetria que sostiene el enlace: el CDR es denso y tiene pocos usuarios, el
# Bip es ralo y tiene millones de tarjetas.

import json

import matplotlib.pyplot as plt
import numpy as np

from reid.config import FIGURAS, RES_CASO

FUENTES = [("cdr", "CDR (telefonía)", "#2c6fbb", "o"),
           ("bip", "Bip (transporte)", "#c0392b", "s")]


def main():
    d = json.loads((RES_CASO / "descripcion_fuentes.json").read_text())

    fig, ax = plt.subplots(figsize=(8, 4.5))

    for clave, etiqueta, color, marca in FUENTES:
        hist = d[clave]["hist_eventos_por_entidad_dia"]
        k = np.array([int(x) for x in hist])
        n = np.array([hist[x] for x in hist], dtype=float)
        frac = 100 * n / n.sum()
        ax.plot(k, frac, marker=marca, markersize=3.5, linewidth=1.5,
                color=color, label=etiqueta, alpha=0.9)
        mediana = d[clave]["mediana_eventos_por_entidad_dia"]
        ax.axvline(mediana, color=color, linestyle="--", linewidth=1, alpha=0.7)
        ax.annotate(f"mediana {mediana}", xy=(mediana * 1.15, frac.max() * 0.5),
                    color=color, fontsize=9)

    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("Eventos que deja una entidad en un día (escala log)")
    ax.set_ylabel("Días de entidad con ese número de eventos (%)")
    ax.set_title("El CDR observa a cada persona muchas veces al día, el Bip dos")
    ax.legend(frameon=False)
    ax.grid(True, alpha=0.3, which="both")
    plt.tight_layout()

    out = FIGURAS / "densidad_fuentes.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    print(f"Guardado en {out}")
    plt.close()


if __name__ == "__main__":
    main()
