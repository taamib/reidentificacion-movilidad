# Tasa de enlace por comuna frente a dos medidas de cobertura del CDR

import pandas as pd
import matplotlib.pyplot as plt

from reid.config import FIGURAS, RES_CASO


def main():
    com = pd.read_csv(RES_CASO / "cobertura_comuna.csv")
    com = com[com["confiable"]]   # el filtro de usuarios minimos lo aplica el analisis

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(9, 4))

    ax1.scatter(com["usuarios"], com["tasa_enlace"] * 100, s=30, color="#c0392b",
                alpha=0.75, edgecolor="white", linewidth=0.5)
    ax1.set_xscale("log")
    ax1.set_xlabel("Usuarios CDR en la comuna (conteo crudo, escala log)")
    ax1.set_ylabel("Fracción bruta de usuarios enlazados (%)")
    ax1.set_title("Cantidad de usuarios CDR observados")
    ax1.grid(True, alpha=0.3, which="both")

    ax2.scatter(com["penetracion"] * 100, com["tasa_enlace"] * 100, s=30, color="#2c6fbb",
                alpha=0.75, edgecolor="white", linewidth=0.5)
    ax2.set_xscale("log")
    ax2.set_xlabel("Cobertura por habitante, penetracion (%, escala log)")
    ax2.set_ylabel("Fracción bruta de usuarios enlazados (%)")
    ax2.set_title("Cobertura del CDR respecto de la población")
    ax2.grid(True, alpha=0.3, which="both")

    plt.tight_layout()
    out = FIGURAS / "comuna_cobertura_penetracion.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    print(f"Guardado en {out}")
    plt.close()


if __name__ == "__main__":
    main()
