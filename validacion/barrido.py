# Barrido de parámetros
# Como cambia el desempeño del enlace al mover una condicion del mundo generado

import time
import traceback
from datetime import datetime

import numpy as np
import pandas as pd

from reid.config import RES_VALIDACION, RADIO_METROS, VENTANA_MINUTOS, MIN_DIAS_COINCIDENCIA
from reid.decision.enlace_mutuo import enlace_mutuo
from validacion import config
from validacion.enlace import enlazar
from validacion.metricas import evaluar
from validacion.sintetico import generar


# Generar un mundo, enlazarlo y evaluarlo
def una_corrida(seed: int, radio_m: int, ventana_min: int, min_dias: int, **mundo) -> dict:
    eventos_A, eventos_B, verdad = generar(seed=seed, **mundo)
    pares = enlazar(eventos_A, eventos_B, radio_m=radio_m, ventana_min=ventana_min)
    return evaluar(enlace_mutuo(pares, min_dias=min_dias), verdad)


# Parametros del metodo
DEL_METODO = {"radio_m": RADIO_METROS, "ventana_min": VENTANA_MINUTOS,
              "min_dias": MIN_DIAS_COINCIDENCIA}


# Un punto de una curva: N_SEMILLAS mundos con los mismos parametros, promediados
def un_punto(parametro: str, valor, n_semillas: int) -> dict:
    metodo = dict(DEL_METODO)
    mundo = {}
    if parametro in metodo:
        metodo[parametro] = valor
    else:
        mundo[parametro] = valor
    corridas = []
    for semilla in range(n_semillas):
        inicio = time.time()
        corridas.append(una_corrida(seed=semilla, **metodo, **mundo))
        ultima = corridas[-1]
        print(f"      semilla {semilla + 1}/{n_semillas}: {time.time() - inicio:.0f} s | "
              f"{ultima['aciertos']} aciertos, {ultima['predichos'] - ultima['aciertos']} falsos",
              flush=True)

    precisiones = np.array([c["precision"] for c in corridas], dtype=float)
    evaluables = int(np.sum(~np.isnan(precisiones))) # conteo de semillas validas
    return {
        parametro: valor,
        "precision": float(np.nanmean(precisiones)) if evaluables else np.nan,
        "n_evaluables": evaluables,
        "precision_std": float(np.nanstd(precisiones)) if evaluables else np.nan,
        "recall": float(np.mean([c["recall"] for c in corridas])),
        "recall_std": float(np.std([c["recall"] for c in corridas])),
        "f1": float(np.mean([c["f1"] for c in corridas])),
        "f1_std": float(np.std([c["f1"] for c in corridas])),
        "verdaderos": int(np.sum([c["verdaderos"] for c in corridas])),
        "aciertos": int(np.sum([c["aciertos"] for c in corridas])),
        "falsos": int(np.sum([c["predichos"] - c["aciertos"] for c in corridas])),
        "n_semillas": n_semillas,
    }


CURVAS = {
    "min_dias":             [2, 3, 4, 5],
    "permanencia_min":      [1, 2, 5, 10, 15, 30],
    "variacion_diaria_min": [0, 5, 9.7, 20, 40],
    "velocidad_m_min":      [40, 80, 160, 330],
    "ruido_espacial_A_m":   [50, 100, 200, 300, 400, 600],
    "n_paraderos":          [50, 100, 205, 400, 1000],
    "ventana_min":          [1, 2, 3, 5, 10, 15],
    "radio_m":              [100, 200, 300, 500, 600, 1000],
    "n_personas":           [10_000, 30_000, 60_000, 150_000],
    "n_dias":               [2, 3, 5, 7, 14, 21, 30],
    "frac_con_cdr":         [0.0066, 0.02, 0.05, 0.1, 0.3, 1.0],
    "dispersion_vagabundeo_m": [500, 1000, 2000, 5000, 20000],
}


def correr(parametro: str, valores: list, n_semillas: int = config.N_SEMILLAS) -> pd.DataFrame:
    print(f"\n{parametro}", flush=True)
    filas = []
    for valor in valores:
        print(f"  {parametro}={valor}", flush=True)
        inicio = time.time()
        filas.append(un_punto(parametro, valor, n_semillas))
        f = filas[-1]
        precision = "  n/a" if f["precision"] != f["precision"] else f"{f['precision']:.3f}"
        print(f"    -> Precision={precision} ({f['n_evaluables']}/{n_semillas})  Recall={f['recall']:.3f}  "
              f"F1={f['f1']:.3f}  falsos={f['falsos']}  "
              f"[{(time.time() - inicio) / 60:.1f} min]\n", flush=True)

        # Guardado incremental
        tabla = pd.DataFrame(filas).assign(
            fecha=datetime.now().isoformat(timespec="seconds"),
            base_n_personas=config.N_PERSONAS,
            base_n_paraderos=config.N_PARADEROS,
            base_n_dias=config.N_DIAS,
            base_radio_m=RADIO_METROS,
            base_ventana_min=VENTANA_MINUTOS,
            base_min_dias=MIN_DIAS_COINCIDENCIA,
        )
        RES_VALIDACION.mkdir(parents=True, exist_ok=True)
        tabla.to_csv(RES_VALIDACION / f"barrido_{parametro}.csv", index=False)
    return tabla


# Todas las curvas, o solo las que se pidan
def correr_curvas(pedidas: list[str] | None = None) -> None:
    pedidas = pedidas or list(CURVAS)
    desconocidas = [p for p in pedidas if p not in CURVAS]
    if desconocidas:
        raise ValueError(f"no existen las curvas {desconocidas}. Las que hay: {', '.join(CURVAS)}")

    inicio = time.time()
    fallaron = []
    for parametro in pedidas:
        try:
            correr(parametro, CURVAS[parametro])
        except Exception:
            fallaron.append(parametro)
            print(f"\n  FALLO la curva {parametro}, se sigue con las demas:", flush=True)
            traceback.print_exc()

    total = time.time() - inicio
    print(f"\nBarrido terminado: {len(pedidas)} curvas en "
          f"{total / 3600:.1f} h ({total / 60:.0f} min)")
    if fallaron:
        print(f"Curvas que fallaron: {', '.join(fallaron)}")

