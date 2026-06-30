# Tasa de enlace por comuna frente a la poblacion, la cobertura del CDR y la pobreza

import unicodedata

import pandas as pd
from scipy import stats

from reid.config import RES_CASO
from reid.config_caso import POBREZA_COMUNAL, MIN_ENTIDADES_GRUPO

COLUMNAS = ["tasa_enlace", "usuarios", "poblacion", "penetracion", "pobreza"]


# Empareja nombres de comuna entre fuentes 
def normalizar(nombre):
    if not isinstance(nombre, str):
        return ""
    s = unicodedata.normalize("NFD", nombre)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return s.lower().replace(" ", "").replace("-", "")


# Matriz de correlaciones de Spearman con su p-valor
def correlaciones(tabla):
    filas = []
    for i, x in enumerate(COLUMNAS):
        for y in COLUMNAS[i+1:]:
            r, p = stats.spearmanr(tabla[x], tabla[y])
            filas.append({"variable_1": x, "variable_2": y,
                          "spearman_r": round(float(r), 3), "p_valor": round(float(p), 4),
                          "n_comunas": len(tabla)})
    return pd.DataFrame(filas)


def main():
    com = pd.read_csv(RES_CASO / "tasa_comuna.csv").rename(columns={"personas": "usuarios"})
    com["clave"] = com["comuna_gadm"].apply(normalizar)

    # Poblacion y pobreza por comuna de la RM 
    info = pd.read_excel(POBREZA_COMUNAL, header=1)
    info = info.rename(columns={info.columns[0]: "CUT", info.columns[2]: "nombre",
                                info.columns[3]: "poblacion", info.columns[5]: "pobreza"})
    info = info[pd.to_numeric(info["CUT"], errors="coerce").notna()].copy()
    info["CUT"] = info["CUT"].astype(int)
    info = info[(info["CUT"] >= 13001) & (info["CUT"] <= 13999)]
    info["clave"] = info["nombre"].apply(normalizar)
    info[["poblacion", "pobreza"]] = info[["poblacion", "pobreza"]].apply(pd.to_numeric,
                                                                         errors="coerce")

    com = com.merge(info[["clave", "poblacion", "pobreza"]], on="clave", how="left")
    com = com.dropna(subset=["poblacion"])
    com["penetracion"] = com["usuarios"] / com["poblacion"]  # cobertura por habitante
    com["confiable"] = com["usuarios"] >= MIN_ENTIDADES_GRUPO

    confiables = com[com["confiable"]]
    print(f"Comunas con datos: {len(com)}  |  con >= {MIN_ENTIDADES_GRUPO} usuarios: {len(confiables)}")

    corr = correlaciones(confiables)
    corr_todas = correlaciones(com)

    print(f"\nSpearman, comunas confiables (>= {MIN_ENTIDADES_GRUPO} usuarios):")
    print(corr[corr["variable_1"] == "tasa_enlace"].to_string(index=False))
    print(f"\nSpearman, las {len(com)} comunas sin filtrar (referencia):")
    print(corr_todas[corr_todas["variable_1"] == "tasa_enlace"].to_string(index=False))

    RES_CASO.mkdir(parents=True, exist_ok=True)
    corr.to_csv(RES_CASO / "correlaciones_comuna.csv", index=False)
    corr_todas.to_csv(RES_CASO / "correlaciones_comuna_sin_filtrar.csv", index=False)

    # La tabla comuna por comuna
    com[["comuna_gadm"] + COLUMNAS + ["confiable"]].to_csv(
        RES_CASO / "cobertura_comuna.csv", index=False)

    print(f"\nGuardado en {RES_CASO / 'correlaciones_comuna.csv'} y {RES_CASO / 'cobertura_comuna.csv'}")


if __name__ == "__main__":
    main()
