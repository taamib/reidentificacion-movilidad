# Cuanto registra cada fuente en cada jornada de la semana enlazada
#
# La semana tiene un feriado y un fin de semana, asi que solo cuatro jornadas son laborales
# normales. El CDR casi no lo nota y el Bip si.

import json

import matplotlib.pyplot as plt
import numpy as np

from reid.config import FIGURAS, RES_CASO

DIA_SEMANA = ["mié", "jue", "vie", "sáb", "dom", "lun", "mar"]


def main():
    d = json.loads((RES_CASO / "descripcion_fuentes.json").read_text())
    fechas = sorted(d["bip"]["eventos_por_dia"])
    tipo = d["tipo_dia"]
    x = np.arange(len(fechas))

    cdr = np.array([d["cdr"]["eventos_por_dia"][f] for f in fechas]) / 1e6
    bip = np.array([d["bip"]["eventos_por_dia"][f] for f in fechas]) / 1e6

    fig, ax = plt.subplots(figsize=(8, 4))

    # Las jornadas que no son laborales normales, de fondo
    for i, f in enumerate(fechas):
        if f in tipo:
            ax.axvspan(i - 0.5, i + 0.5, color="#cccccc", alpha=0.45, linewidth=0)

    ancho = 0.38
    ax.bar(x - ancho/2, cdr, ancho, color="#2c6fbb", label="CDR (telefonía)")
    ax.bar(x + ancho/2, bip, ancho, color="#c0392b", label="Bip (transporte)")
    for i, (a, b) in enumerate(zip(cdr, bip)):
        ax.text(i - ancho/2, a + 0.08, f"{a:.2f}", ha="center", fontsize=8, color="#2c6fbb")
        ax.text(i + ancho/2, b + 0.08, f"{b:.2f}", ha="center", fontsize=8, color="#c0392b")

    ax.set_xticks(x)
    ax.set_xticklabels([f"{DIA_SEMANA[i]}\n{f[-2:]} nov" for i, f in enumerate(fechas)])
    ax.set_ylabel("Eventos de la fuente (millones)")
    ax.set_ylim(top=bip.max() * 1.28)
    ax.legend(frameon=False, ncol=2, loc="upper left")
    ax.grid(True, axis="y", alpha=0.3)
    ax.set_title("Solo cuatro de las siete jornadas son laborales normales")

    plt.tight_layout()
    out = FIGURAS / "volumen_por_jornada.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    print(f"Guardado en {out}")
    plt.close()


if __name__ == "__main__":
    main()
