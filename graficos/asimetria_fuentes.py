# La semana de una entidad tipica en cada fuente
#
# El Bip aporta mas datos y muchas mas entidades distintas, pero cada tarjeta deja muy poco
# rastro. Esta figura dibuja, punto por punto, lo que registra cada fuente sobre una entidad
# mediana durante los siete dias.


import matplotlib.pyplot as plt

from reid.config import FIGURAS

AZUL, ROJO = "#2c6fbb", "#c0392b"
# Los dias van sin nombre porque el reparto es ilustrativo, no una semana real
DIA = [f"día {i}" for i in range(1, 8)]


# Reparte los eventos de la semana entre los dias activos, lo mas parejo posible
def reparto(total, dias_activos, n_dias=7):
    base, resto = divmod(total, dias_activos)
    por_dia = [base + (1 if i < resto else 0) for i in range(dias_activos)]
    # los dias sin actividad se dejan al final de la semana
    return por_dia + [0] * (n_dias - dias_activos)


def fila(ax, y, total, dias_activos, color, etiqueta):
    for dia, n in enumerate(reparto(total, dias_activos)):
        if n == 0:
            continue
        # los puntos del dia se apilan en una columnita angosta
        xs, ys = [], []
        for k in range(n):
            xs.append(dia + 0.30 + (k % 4) * 0.14)
            ys.append(y - 0.32 + (k // 4) * 0.075)
        ax.scatter(xs, ys, s=11, color=color, edgecolors="none")
    ax.text(-0.25, y - 0.15, etiqueta, ha="right", va="center", fontsize=11, color=color,
            fontweight="bold")


def main():
    fig, ax = plt.subplots(figsize=(8, 3.4))

    fila(ax, 1.1, 141, 6, AZUL, "CDR\n141 registros\nen 6 días")
    fila(ax, 0.0, 4, 2, ROJO, "Bip\n4 registros\nen 2 días")

    for x in range(1, 7):
        ax.axvline(x, color="#dddddd", linewidth=0.8)
    ax.set_xticks([i + 0.5 for i in range(7)])
    ax.set_xticklabels(DIA)
    ax.set_xlim(-2.5, 7)
    ax.set_ylim(-0.55, 2.1)
    ax.set_yticks([])
    for lado in ("top", "right", "left"):
        ax.spines[lado].set_visible(False)
    ax.set_title("Lo que cada fuente registra sobre una entidad típica en la semana")
    plt.tight_layout()

    out = FIGURAS / "asimetria_fuentes.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    print(f"Guardado en {out}")
    plt.close()


if __name__ == "__main__":
    main()
