# Cobertura horaria de las dos fuentes
#
# Muestra en que horas del dia observa cada fuente. El CDR no cubre la noche, asi que hay
# franjas donde una fuente ve y la otra no, y ahi no puede haber co-ocurrencias.

import json

import matplotlib.pyplot as plt
import numpy as np

from reid.config import FIGURAS, RES_CASO


def main():
    d = json.loads((RES_CASO / "descripcion_fuentes.json").read_text())
    cdr = 100 * np.array(d["cdr"]["por_hora"])
    bip = 100 * np.array(d["bip"]["por_hora"])
    ciegas = d["horas_ciegas_cdr"]
    horas = np.arange(24)

    fig, ax = plt.subplots(figsize=(8, 4))

    # Las horas sin cobertura del CDR, de fondo
    for h in ciegas:
        ax.axvspan(h - 0.5, h + 0.5, color="#cccccc", alpha=0.45, linewidth=0)

    ax.plot(horas, cdr, marker="o", markersize=4, linewidth=1.8,
            color="#2c6fbb", label="CDR (telefonía)")
    ax.plot(horas, bip, marker="s", markersize=4, linewidth=1.8,
            color="#c0392b", label="Bip (transporte)")


    ax.set_xticks(range(0, 24, 2))
    ax.set_xlim(-0.5, 23.5)
    ax.set_ylim(bottom=0)
    ax.set_xlabel("Hora del día")
    ax.set_ylabel("Eventos de la fuente en esa hora (%)")
    ax.set_title("El CDR y el Bip no observan a las mismas horas")
    ax.legend(frameon=False)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()

    out = FIGURAS / "cobertura_horaria.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    print(f"Guardado en {out}")
    plt.close()


if __name__ == "__main__":
    main()
