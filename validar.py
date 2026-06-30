# Validación del framework, instanciada sobre las fuentes del caso CDR-Bip
import sys
import time

import pandas as pd

from reid.config import RES_VALIDACION, RADIO_METROS, VENTANA_MINUTOS
from reid.fuentes.bip import cargar_eventos as cargar_bip
from reid.fuentes.cdr import cargar_eventos as cargar_cdr
from validacion import anclaje as medir_anclaje
from validacion import barrido as correr_barrido
from validacion.azar import test_de_azar
from validacion.optimalidad import calibrar, correr, elegidos, resumir
from validacion.semisintetico import partir_en_dos, primeros_dias
from validacion.sintetico import generar

N_DIAS = 7          # los que cubre el Bip
UMBRALES_AZAR = [1, 2, 3, 4, 5]
N_BARAJADAS = 30

# Por defecto la optimalidad prueba la grilla entera, con esto se puede pedir solo un subconjunto de radios y ventanas
def grilla_pedida(argumentos: list[str]) -> dict:
    if len(argumentos) < 2:
        return {}
    return {"radios": [int(r) for r in argumentos[0].split(",")],
            "ventanas": [int(v) for v in argumentos[1].split(",")]}


# Guarda la tabla. Si solo se pidieron puntos nuevos, se agregan a los que ya estaban.
def guardar(tabla: pd.DataFrame, nombre: str, agregar: bool) -> None:
    salida = RES_VALIDACION / f"optimalidad_{nombre}.csv"
    if agregar and salida.exists():
        tabla = pd.concat([pd.read_csv(salida), tabla], ignore_index=True)
    tabla.to_csv(salida, index=False)
    resumir(tabla)

    # Ademas del detalle, una tabla chica con solo lo que gano en cada mundo
    resumen_de_todos = RES_VALIDACION / "optimalidad_elegidos.csv"
    ganadores = elegidos(tabla).assign(mundo=nombre)
    if resumen_de_todos.exists():
        previos = pd.read_csv(resumen_de_todos)
        ganadores = pd.concat([previos[previos["mundo"] != nombre], ganadores], ignore_index=True)
    ganadores.to_csv(resumen_de_todos, index=False)

    print(f"\nGuardado en {salida} y en {resumen_de_todos}")


# Un mundo inventado entero: hay verdad conocida, así que se pueden comparar los dos criterios
def sintetico(grilla: dict) -> None:
    print("Generando el mundo sintetico...", flush=True)
    eventos_A, eventos_B, verdad = generar(seed=0)
    print(f"  {len(eventos_A):,} eventos A | {len(eventos_B):,} B | "
          f"{len(verdad):,} pares verdaderos\n", flush=True)
    guardar(correr(eventos_A, eventos_B, verdad=verdad, **grilla), "sintetico", bool(grilla))


# El CDR real partido en dos mitades de eventos
def semisintetico(grilla: dict) -> None:
    print("Cargando el CDR y partiendolo en dos...", flush=True)
    eventos_A, eventos_B, verdad = partir_en_dos(primeros_dias(cargar_cdr(), N_DIAS), seed=0)
    print(f"  {len(eventos_A):,} eventos A | {len(eventos_B):,} B | "
          f"{len(verdad):,} pares verdaderos\n", flush=True)
    guardar(correr(eventos_A, eventos_B, verdad=verdad, **grilla), "semisintetico", bool(grilla))


# El cruce real
def caso(grilla: dict) -> None:
    print("Cargando el caso real...", flush=True)
    cdr = primeros_dias(cargar_cdr(), N_DIAS)
    bip = cargar_bip()
    guardar(calibrar(cdr, bip, guardar_parciales_en=RES_VALIDACION, **grilla),
            "caso", bool(grilla))


# El test del azar sobre la población completa, que es la que reporta el caso
def azar() -> None:
    print("Cargando el caso completo...", flush=True)
    A = primeros_dias(cargar_cdr(), N_DIAS)
    B = cargar_bip()
    print(f"  A {len(A):,} eventos | B {len(B):,} eventos", flush=True)

    tabla = test_de_azar(A, B, UMBRALES_AZAR, N_BARAJADAS,
                         radio_m=RADIO_METROS, ventana_min=VENTANA_MINUTOS)
    salida = RES_VALIDACION / "azar_por_umbral_dias.csv"
    tabla.to_csv(salida, index=False)
    print(f"\nGuardado en {salida}")


ETAPAS = {"anclaje": medir_anclaje.medir, "barrido": correr_barrido.correr_curvas, "azar": azar}

MUNDOS = {"sintetico": sintetico, "semisintetico": semisintetico, "caso": caso}

USO = ("uso:  python validar.py <etapa>\n"
       f"      etapas: {', '.join(ETAPAS)}\n"
       f"      python validar.py optimalidad <mundo> [radios ventanas]\n"
       f"      mundos: {', '.join(MUNDOS)}")


def main() -> None:
    etapa = sys.argv[1] if len(sys.argv) > 1 else None
    mundo = sys.argv[2] if len(sys.argv) > 2 else None
    if etapa not in ETAPAS and not (etapa == "optimalidad" and mundo in MUNDOS):
        sys.exit(USO)

    inicio = time.time()
    RES_VALIDACION.mkdir(parents=True, exist_ok=True)
    if etapa == "optimalidad":
        MUNDOS[mundo](grilla_pedida(sys.argv[3:]))
    else:
        ETAPAS[etapa]()
    print(f"Terminado en {(time.time() - inicio) / 60:.1f} min")


if __name__ == "__main__":
    main()
