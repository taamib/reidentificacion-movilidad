# Sensibilidad del resultado real a la cantidad de dias de Bip usados 
import pandas as pd
import matplotlib.pyplot as plt

from reid.config import FIGURAS, RES_VALIDACION


def main():
    tabla = pd.read_csv(RES_VALIDACION / "sensibilidad_dias.csv")

    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot(tabla["dias_usados"], tabla["pct_enlazados"], marker="o", color="#c0392b")
    for x, y in zip(tabla["dias_usados"], tabla["pct_enlazados"]):
        ax.annotate(f"{y:.2f}%", (x, y), textcoords="offset points", xytext=(0, 8), ha="center", fontsize=9)

    ax.set_xticks(tabla["dias_usados"])
    ax.set_ylim(0, tabla["pct_enlazados"].max() * 1.15)
    ax.set_xlabel("Días de Bip usados")
    ax.set_ylabel("Usuarios enlazados (%)")
    ax.set_title("La tasa bruta de enlace no se estabiliza a los 7 días")
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    out = FIGURAS / "sensibilidad_dias.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    print(f"Guardado en {out}")
    plt.close()


if __name__ == "__main__":
    main()
