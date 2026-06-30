# Autocorrelacion espacial de la tasa de enlace por comuna

import json
import pandas as pd
import numpy as np
from libpysal.weights import Queen
from esda.moran import Moran, Moran_Local

from reid.config import RES_CASO
from reid.config_caso import MIN_ENTIDADES_GRUPO
from reid.aplicacion.hogar import cargar_comunas_rm


def main():
    # Leer resultados de tasa por comuna 
    tabla = pd.read_csv(RES_CASO / "tasa_comuna.csv")

    comunas = cargar_comunas_rm()
    geo = comunas.merge(tabla, on="comuna_gadm", how="inner")
    geo = geo[geo["personas"] >= MIN_ENTIDADES_GRUPO].reset_index(drop=True)
    print(f"Comunas en el analisis (>= {MIN_ENTIDADES_GRUPO} usuarios): {len(geo)}")

    # Dos comunas son vecinas si comparten borde
    w = Queen.from_dataframe(geo, use_index=False)
    w.transform = "r"  # cada comuna promedia a sus vecinas

    np.random.seed(0)
    mi = Moran(geo["tasa_enlace"].values, w, permutations=999)
    print(f"\nMoran's I global: I = {mi.I:+.3f}  (esperado al azar ~ {mi.EI:+.3f})")
    print(f"  p-valor (999 permutaciones): {mi.p_sim:.3f}")
    tendencia = "agrupada" if mi.I > 0 else "dispersa"
    print(f"  Interpretacion: la tasa esta {tendencia} en el espacio"
          + (" (significativo)" if mi.p_sim < 0.05 else " (no significativo)"))

    lisa = Moran_Local(geo["tasa_enlace"].values, w, permutations=999, seed=0)
    etiquetas = {1: "Alto-Alto", 2: "Bajo-Alto", 3: "Bajo-Bajo", 4: "Alto-Bajo"}
    geo["cluster"] = [etiquetas[q] if p < 0.05 else "No significativo"
                      for q, p in zip(lisa.q, lisa.p_sim)]
    geo["p_sim_local"] = lisa.p_sim

    print("\nComunas por tipo de cluster (LISA, p < 0.05):")
    print(geo["cluster"].value_counts().to_string())

    # Moran global y LISA se guardan para dibujar figuras
    RES_CASO.mkdir(parents=True, exist_ok=True)
    (RES_CASO / "moran_comuna.json").write_text(json.dumps({
        "moran_I": round(float(mi.I), 3), "p_sim": round(float(mi.p_sim), 3),
        "n_comunas": int(len(geo)), "min_usuarios": MIN_ENTIDADES_GRUPO, "escala": "comuna",
    }, indent=2, ensure_ascii=False))

    # La clasificacion comuna por comuna
    (geo[["comuna_gadm", "personas", "tasa_enlace", "cluster", "p_sim_local"]]
        .sort_values(["cluster", "comuna_gadm"])
        .to_csv(RES_CASO / "lisa_comuna.csv", index=False))

    print(f"\nGuardado en {RES_CASO / 'moran_comuna.json'} y {RES_CASO / 'lisa_comuna.csv'}")


if __name__ == "__main__":
    main()
