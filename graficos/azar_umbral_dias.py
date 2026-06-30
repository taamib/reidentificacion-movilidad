# Real vs. azar por umbral de dias de coincidencia, para el caso CDR-Bip

import pandas as pd
import matplotlib.pyplot as plt

from reid.config import FIGURAS, RES_VALIDACION


def main():
    tabla = pd.read_csv(RES_VALIDACION / "azar_por_umbral_dias.csv")
    if "completo" in tabla and not tabla["completo"].all():
        raise ValueError("el resumen de azar todavía está incompleto; no se genera la figura final")
    n_shuffles = int(tabla["n_shuffles"].min()) if "n_shuffles" in tabla else 30

    fig, ax = plt.subplots(figsize=(7, 5))
    x = tabla["umbral_dias"]
    ancho = 0.35

    ax.bar(x - ancho / 2, tabla["real"], width=ancho, color="#c0392b", label="Enlace mutuo (observado)")
    ax.bar(x + ancho / 2, tabla["azar_media"], width=ancho, color="#95a5a6",
           yerr=tabla["azar_std"], capsize=4, error_kw={"ecolor": "#333333", "elinewidth": 1.2},
           label=f"Azar (promedio de {n_shuffles} barajadas)")

    for xi, real, azar in zip(x, tabla["real"], tabla["azar_media"]):
        ax.text(xi, max(real, azar) + 60, f"{100*azar/real:.0f}% azar", ha="center", fontsize=8)

    ax.set_ylim(0, tabla["real"].max() * 1.18)
    ax.set_xticks(x)
    ax.set_xlabel("Umbral de repetición (días)")
    ax.set_ylabel("Usuarios enlazados")
    ax.set_title("El azar explica una fracción decreciente del enlace mutuo a más días")
    ax.legend(loc="upper right", bbox_to_anchor=(1, 0.93))
    ax.grid(True, axis="y", alpha=0.3)
    plt.tight_layout()
    out = FIGURAS / "azar_umbral_dias.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    print(f"Guardado en {out}")
    plt.close()


if __name__ == "__main__":
    main()
