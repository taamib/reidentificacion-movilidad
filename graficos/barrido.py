# Las curvas del barrido sintetico: precision, recall y F1 al mover un parametro del generador
import sys

import pandas as pd
import matplotlib.pyplot as plt

from reid.config import FIGURAS, RES_VALIDACION

# Que dice el eje x y el titulo de cada curva. Agregar una curva es agregar una linea aca.
EJES = {
    "radio_m":                 ("Radio de enlace (m)", "El radio decide el canje entre precision y recall"),
    "ventana_min":             ("Ventana temporal (min)", "Ampliar la ventana suma candidatos verdaderos y falsos"),
    "min_dias":                ("Minimo de dias de coincidencia", "Exigir mas dias sube la precision y hunde el recall"),
    "permanencia_min":         ("Permanencia en el paradero (min)", "El efecto de la permanencia se satura a los 5 minutos"),
    "variacion_diaria_min":    ("Variacion diaria de la rutina (min)", "La puntualidad de las personas casi no mueve el resultado"),
    "velocidad_m_min":         ("Velocidad de alejamiento (m/min)", "Alejarse rapido del paradero destruye las co-ocurrencias"),
    "ruido_espacial_A_m":      ("Ruido espacial de la fuente A (m)", "El error de antena es lo que mas castiga al enlace"),
    "dispersion_vagabundeo_m": ("Dispersion del vagabundeo (m)", "Concentrar a la gente en su barrio derrumba la precision"),
    "n_paraderos":             ("Paraderos en la ciudad", "Mas paraderos reparten la competencia y suben la precision"),
    "n_personas":              ("Personas en el mundo generado", "Mas gente en la misma ciudad significa mas confusion"),
    "n_dias":                  ("Dias observados", "Cada dia adicional aporta evidencia"),
    "frac_con_cdr":            ("Fraccion de la poblacion con CDR", "La competencia no la fija cuanta gente esta en las dos fuentes"),
}

# Las tres metricas, con su color. La precision va en el eje de la izquierda y las otras dos en el
# de la derecha, porque la precision vale del orden de 0,5 y el recall del orden de 0,02: en un
# mismo eje las dos curvas chicas quedarian pegadas al suelo.
IZQUIERDA = ("precision", "Precision", "#c0392b")
DERECHA = [("recall", "Recall", "#2874a6"), ("f1", "F1", "#1e8449")]


# Una curva con barras de mas menos una desviacion entre las semillas del punto
def curva(eje, x: pd.Series, tabla: pd.DataFrame, columna: str, etiqueta: str, color: str):
    return eje.errorbar(x, tabla[columna], yerr=tabla[f"{columna}_std"],
                        marker="o", color=color, label=etiqueta,
                        capsize=3, elinewidth=1, markersize=5)


def figura(parametro: str) -> None:
    tabla = pd.read_csv(RES_VALIDACION / f"barrido_{parametro}.csv")
    etiqueta_x, titulo = EJES[parametro]
    x = tabla[parametro]

    fig, izquierdo = plt.subplots(figsize=(7.5, 4.5))
    derecho = izquierdo.twinx()

    lineas = [curva(izquierdo, x, tabla, *IZQUIERDA)]
    lineas += [curva(derecho, x, tabla, *metrica) for metrica in DERECHA]

    izquierdo.set_xlabel(etiqueta_x)
    izquierdo.set_ylabel("Precision", color=IZQUIERDA[2])
    izquierdo.tick_params(axis="y", labelcolor=IZQUIERDA[2])
    izquierdo.set_ylim(0, 1)
    derecho.set_ylabel("Recall y F1")
    derecho.set_ylim(0, None)

    # Los parametros que se barren en potencias de diez se leen mejor en escala logaritmica
    if x.max() / max(x.min(), 1e-9) >= 100:
        izquierdo.set_xscale("log")
    else:
        izquierdo.set_xticks(x)

    # Donde alguna semilla no propuso ningun enlace la precision quedo indefinida y el promedio
    # se hizo sobre menos semillas, asi que hay que decirlo
    faltan = tabla["n_evaluables"] < tabla["n_semillas"]
    for xi, yi, n in zip(x[faltan], tabla.loc[faltan, "precision"], tabla.loc[faltan, "n_evaluables"]):
        izquierdo.annotate(f"{n} semillas", (xi, yi), textcoords="offset points",
                           xytext=(0, 10), ha="center", fontsize=8, color="#7f8c8d")

    izquierdo.grid(True, alpha=0.3)
    izquierdo.legend(lineas, [l.get_label() for l in lineas], loc="best")
    n = int(tabla["n_semillas"].iloc[0])
    izquierdo.set_title(f"{titulo}\n(promedio de {n} semillas; las barras son una desviacion entre ellas)",
                        fontsize=11)
    plt.tight_layout()

    salida = FIGURAS / f"barrido_{parametro}.png"
    fig.savefig(salida, dpi=150, bbox_inches="tight")
    print(f"Guardado en {salida}")
    plt.close()


def main() -> None:
    pedidos = sys.argv[1:] or list(EJES)
    for parametro in pedidos:
        if parametro not in EJES:
            sys.exit(f"no existe la curva '{parametro}'. Las que hay: {', '.join(EJES)}")
        figura(parametro)


if __name__ == "__main__":
    main()
