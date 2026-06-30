# El ritmo del CDR y cuanto del dia alcanza a cubrir
#
# El CDR llega en rafagas separadas por silencios largos. Con la ventana de coincidencia
# del metodo, cada usuario queda visible solo una fraccion chica de la jornada, y eso pone
# un techo a cuantas validaciones Bip pueden llegar a coincidir con un ping.

import json

import matplotlib.pyplot as plt
import numpy as np

from reid.config import FIGURAS, RES_CASO
from reid.config import VENTANA_MINUTOS


def main():
    r = json.loads((RES_CASO / "descripcion_fuentes.json").read_text())["ritmo_cdr"]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(8, 3.6))

    # Izquierda: cada cuanto llega el siguiente ping
    q = r["huecos_min"]
    pct = np.array([int(k[1:]) for k in q])
    val = np.array([q[k] for k in q])
    ax1.plot(val, pct, marker="o", markersize=5, linewidth=1.8, color="#2c6fbb")
    ax1.axvline(VENTANA_MINUTOS, color="#c0392b", linestyle="--", linewidth=1.2)
    ax1.annotate(f"ventana del método\n±{VENTANA_MINUTOS} min", xy=(VENTANA_MINUTOS * 1.25, 32),
                 fontsize=9, color="#c0392b")
    ax1.set_xscale("log")
    ax1.set_xlabel("Minutos hasta el siguiente ping (escala log)")
    ax1.set_ylabel("Huecos por debajo de ese valor (%)")
    ax1.set_title("El CDR llega en ráfagas")
    ax1.grid(True, alpha=0.3, which="both")

    # Derecha: cuanto del dia observado queda cubierto segun la ventana
    cob = r["cobertura_por_ventana"]
    w = np.array([int(k) for k in cob])
    f = 100 * np.array([cob[k] for k in cob])
    ax2.plot(w, f, marker="o", markersize=5, linewidth=1.8, color="#2c6fbb")
    elegido = cob[str(VENTANA_MINUTOS)]
    ax2.plot([VENTANA_MINUTOS], [100 * elegido], marker="o", markersize=9, color="#c0392b")
    ax2.annotate(f"±{VENTANA_MINUTOS} min → {100*elegido:.1f}%",
                 xy=(VENTANA_MINUTOS + 1.5, 100 * elegido - 1), fontsize=9, color="#c0392b")
    ax2.set_xlabel("Semiventana de coincidencia (minutos)")
    ax2.set_ylabel("Jornada observada cubierta (%)")
    ax2.set_title("Cuánto del día queda a tiro de un ping")
    ax2.set_ylim(0, 100)
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    out = FIGURAS / "ritmo_cdr.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    print(f"Guardado en {out}")
    plt.close()


if __name__ == "__main__":
    main()
