# Generador de datos sintéticos con verdad conocida
import numpy as np
import pandas as pd

from validacion import config


# Sortear n valores enteros respetando su frecuencia real
def sortear_de_tabla(tabla: tuple[int, ...], n: int, rng: np.random.Generator) -> np.ndarray:
    valores = np.arange(1, len(tabla) + 1)
    pesos = np.asarray(tabla, dtype=float)
    return rng.choice(valores, size=n, p=pesos / pesos.sum())


# Sortear n valores continuos, interpolando en la curva de percentiles medida
def sortear_de_percentiles(percentiles: dict[float, float], n: int,
                           rng: np.random.Generator) -> np.ndarray:
    p = np.array(sorted(percentiles))
    v = np.array([percentiles[x] for x in p], dtype=float)
    return np.interp(rng.random(n), p, v)


# Sortear n horarios habituales del perfil horario del paradero, en minutos del dia
def sortear_hora_habitual(perfil: dict[int, float], n: int,
                          rng: np.random.Generator) -> np.ndarray:
    horas = np.array(list(perfil.keys()))
    pesos = np.array(list(perfil.values()), dtype=float)
    elegidas = rng.choice(horas, size=n, p=pesos / pesos.sum())
    return (elegidas + rng.random(n)) * 60   # un minuto cualquiera dentro de esa hora


METROS_POR_GRADO_LAT = 111_320
LAT_REF = -33.45   # a la altura de Santiago un grado de longitud cubre menos que uno de latitud


# Un desplazamiento en metros pasado a grados. La longitud se corrige por la latitud
def metros_a_grados(d_lat_m: np.ndarray, d_lon_m: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    return (d_lat_m / METROS_POR_GRADO_LAT,
            d_lon_m / (METROS_POR_GRADO_LAT * np.cos(np.radians(LAT_REF))))


# La ciudad

# Crea los paraderos de la ciudad con su ubicacion y demanda relativa
def crear_ciudad(n_paraderos: int, tarjetas_por_paradero: dict[float, float],
                 rng: np.random.Generator) -> pd.DataFrame:
    demanda = sortear_de_percentiles(tarjetas_por_paradero, n_paraderos, rng)
    return pd.DataFrame({
        "lat": rng.uniform(config.LAT_MIN, config.LAT_MAX, n_paraderos),
        "lon": rng.uniform(config.LON_MIN, config.LON_MAX, n_paraderos),
        "peso": demanda / demanda.sum(), # con que probabilidad una persona elige este paradero
    })


# Los lugares de cada persona

# Que paraderos usa una persona, y a que hora suele llegar a cada uno
def elegir_lugares(n_lugares: int, ciudad: pd.DataFrame, perfil_horario: dict[int, float],
                   rng: np.random.Generator) -> tuple[np.ndarray, np.ndarray]:
    lugares = rng.choice(len(ciudad), size=n_lugares, replace=False, p=ciudad["peso"].to_numpy())
    hora_habitual = sortear_hora_habitual(perfil_horario, n_lugares, rng)
    return lugares, hora_habitual


# Las visitas

# Como reparte una persona sus validaciones entre sus lugares, del mas al menos usado
def pesos_por_rango(n_lugares: int, perfil: tuple[int, ...]) -> np.ndarray:
    return np.array([perfil[min(i, len(perfil) - 1)] for i in range(n_lugares)], dtype=float)


# Reparte las validaciones de una persona entre sus lugares y sus dias
def repartir_visitas(n_validaciones: int, n_lugares: int, n_dias: int, perfil: tuple[int, ...],
                     rng: np.random.Generator) -> list[tuple[int, int]]:
    pesos = pesos_por_rango(n_lugares, perfil)
    por_lugar = rng.multinomial(n_validaciones, pesos / pesos.sum())

    visitas = []
    for rango, cuantas in enumerate(por_lugar):
        for dia in rng.choice(n_dias, size=min(cuantas, n_dias), replace=False):
            visitas.append((rango, int(dia)))
    return visitas


# Fuente 0
# Decide donde y cuando estuvo cada persona, antes de que ninguna fuente la observe. Esta es la verdad conocida
def visitas_verdaderas(ciudad: pd.DataFrame, n_personas: int, n_dias: int,
                       lugares_por_persona: tuple[int, ...],
                       actividad_por_persona: tuple[int, ...], perfil_rango: tuple[int, ...],
                       perfil_horario: dict[int, float], variacion_diaria_min: float,
                       rng: np.random.Generator) -> pd.DataFrame:
    # Cuantos lugares usa cada persona
    n_lugares = sortear_de_tabla(lugares_por_persona, n_personas, rng) 
    n_lugares = np.minimum(n_lugares, len(ciudad)) 

    # Cuantas validaciones esperadas por persona
    esperadas = sortear_de_tabla(actividad_por_persona, n_personas, rng) * n_dias / config.DIAS_MEDIDOS
    n_validaciones = np.floor(esperadas).astype(int)
    # Sale float asi que hay que redondear pero eso sesga, así que se sortea un 0 o 1 extra con probabilidad igual a la parte decimal
    n_validaciones += (rng.random(n_personas) < esperadas % 1)

    filas = []
    for persona in range(n_personas):
        # Cuales paraderos usa y a que hora suele llegar a cada uno
        lugares, hora_habitual = elegir_lugares(n_lugares[persona], ciudad, perfil_horario, rng)
        # Repartir las validaciones de la persona entre sus lugares y dias, y sortear la hora de cada una
        for rango, dia in repartir_visitas(n_validaciones[persona], len(lugares), n_dias,
                                           perfil_rango, rng):
            # Su horario habitual en ese lugar, mas la variacion de ese dia en particular
            minuto = hora_habitual[rango] + rng.normal(0, variacion_diaria_min)
            filas.append((persona, lugares[rango], dia, minuto))

    return pd.DataFrame(filas, columns=["persona", "paradero", "dia", "minuto"])


# Fuente B
# El Bip registra la validacion en la coordenada exacta del paradero
def observa_bip(visitas: pd.DataFrame, ciudad: pd.DataFrame) -> pd.DataFrame:
    paradero = visitas["paradero"].to_numpy()
    return visitas.assign(lat=ciudad["lat"].to_numpy()[paradero],
                          lon=ciudad["lon"].to_numpy()[paradero])


# Decide cuando pinguea un celular para cada persona y dia
def sortear_pings(n_personas: int, n_dias: int, pings_por_dia: dict[float, float],
                  hueco_entre_pings_min: dict[float, float],
                  rng: np.random.Generator) -> pd.DataFrame:
    minuto_inicio, largo_dia = config.HORA_INICIO * 60, (config.HORA_FIN - config.HORA_INICIO) * 60
    # Cuantos pings tiene cada persona y dia, sorteando de la distribucion real
    cuantos = sortear_de_percentiles(pings_por_dia, n_personas * n_dias, rng)
    cuantos = np.maximum(cuantos.round().astype(int), 1)

    personas, dias, minutos = [], [], []
    for k, n in enumerate(cuantos):
        # primeros n_dias valores son de la persona 0, los siguientes n_dias de la persona 1, etc
        persona, dia = divmod(k, n_dias)
        # sortear tiempos entre pings de acuerdo a la distribucion real que vienen en rafagas
        huecos = sortear_de_percentiles(hueco_entre_pings_min, n, rng)
        desde_el_primero = np.cumsum(huecos) - huecos[0]
        arranque = rng.random() * largo_dia

        minutos.append(minuto_inicio + (arranque + desde_el_primero) % largo_dia)
        personas.append(np.full(n, persona))
        dias.append(np.full(n, dia))

    return pd.DataFrame({"persona": np.concatenate(personas),
                         "dia": np.concatenate(dias),
                         "minuto": np.concatenate(minutos)})


# Le da a cada ping un paradero de su propia persona
def sortear_paradero_propio(persona: np.ndarray, visitas: pd.DataFrame,
                            rng: np.random.Generator) -> np.ndarray:
    propios = visitas[["persona", "paradero"]].drop_duplicates().sort_values("persona")
    paraderos = propios["paradero"].to_numpy()
    cuantos = np.bincount(propios["persona"].to_numpy(), minlength=persona.max() + 1)
    inicio = np.concatenate([[0], np.cumsum(cuantos)[:-1]])
    return paraderos[inicio[persona] + (rng.random(len(persona)) * cuantos[persona]).astype(int)]


# Fuente A
# Decide donde ubicar cada ping
def observa_cdr(visitas: pd.DataFrame, ciudad: pd.DataFrame, n_personas: int, n_dias: int,
                pings_por_dia: dict[float, float], hueco_entre_pings_min: dict[float, float],
                permanencia_min: float, velocidad_m_min: float, ruido_espacial_m: float,
                dispersion_vagabundeo_m: float, rng: np.random.Generator) -> pd.DataFrame:
    pings = sortear_pings(n_personas, n_dias, pings_por_dia, hueco_entre_pings_min, rng)
    pings["id"] = np.arange(len(pings))

    # Asocia cada ping con la visita mas cercana en el tiempo, si esta dentro del umbral de permanencia
    cerca = pings.merge(visitas, on=["persona", "dia"], suffixes=("", "_visita"))
    cerca["desfase"] = (cerca["minuto"] - cerca["minuto_visita"]).abs()
    cerca = cerca[cerca["desfase"] <= permanencia_min].sort_values("desfase")
    mas_cercana = cerca.drop_duplicates("id").set_index("id")
    pings["paradero"] = pings["id"].map(mas_cercana["paradero"])
    pings["desfase"] = pings["id"].map(mas_cercana["desfase"])

    # Pings que no cayeron junto a una visita se ubican dentro del barrio de la persona
    vaga = sortear_paradero_propio(pings["persona"].to_numpy(), visitas, rng)
    vaga_lat, vaga_lon = metros_a_grados(
        rng.normal(0, dispersion_vagabundeo_m, len(pings)),
        rng.normal(0, dispersion_vagabundeo_m, len(pings)))

    # Ubica cada ping en la coordenada del paradero si cae junto a una visita, o en su barrio
    en_paradero = pings["paradero"].notna().to_numpy()
    indice = pings["paradero"].fillna(0).astype(int).to_numpy()
    lat = np.where(en_paradero, ciudad["lat"].to_numpy()[indice],
                   ciudad["lat"].to_numpy()[vaga] + vaga_lat)
    lon = np.where(en_paradero, ciudad["lon"].to_numpy()[indice],
                   ciudad["lon"].to_numpy()[vaga] + vaga_lon)

    # Desplazamiento de una persona entre validacion y ping, con una velocidad que se barre
    alejamiento = velocidad_m_min * np.nan_to_num(pings["desfase"].to_numpy())
    rumbo = rng.uniform(0, 2 * np.pi, len(pings))   
    mov_lat, mov_lon = metros_a_grados(alejamiento * np.cos(rumbo), alejamiento * np.sin(rumbo))

    # Ruido espacial por la antena, encima de donde la persona realmente estaba
    d_lat, d_lon = metros_a_grados(rng.normal(0, ruido_espacial_m, len(pings)),
                                   rng.normal(0, ruido_espacial_m, len(pings)))
    return pings.assign(lat=lat + mov_lat + d_lat, lon=lon + mov_lon + d_lon)



# Al esquema canonico que espera reid/
# Los identificadores son enteros de 32 bits, asi que se les suma un desplazamiento a los de la fuente B para que no se solapen con los de A
def a_esquema(eventos: pd.DataFrame, fuente: str) -> pd.DataFrame:
    desplazamiento = 1 << 24 if fuente == "B" else 0
    return pd.DataFrame({
        "entidad_id": eventos["persona"].to_numpy() + desplazamiento,
        "lat": eventos["lat"].to_numpy(),
        "lon": eventos["lon"].to_numpy(),
        "timestamp": (config.FECHA_BASE
                      + pd.to_timedelta(eventos["dia"].to_numpy(), unit="D")
                      + pd.to_timedelta(eventos["minuto"].to_numpy(), unit="m")),
        "fuente": fuente,
    })


# Devuelve (eventos_A, eventos_B, verdad)
def generar(
    n_personas: int = config.N_PERSONAS,
    n_paraderos: int = config.N_PARADEROS,
    n_dias: int = config.N_DIAS,
    tarjetas_por_paradero: dict[float, float] = config.TARJETAS_POR_PARADERO,
    lugares_por_persona: tuple[int, ...] = config.LUGARES_POR_PERSONA,
    actividad_por_persona: tuple[int, ...] = config.ACTIVIDAD_POR_PERSONA,
    perfil_rango: tuple[int, ...] = config.PERFIL_RANGO,
    perfil_horario: dict[int, float] = config.PERFIL_HORARIO,
    variacion_diaria_min: float = config.VARIACION_DIARIA_MIN,
    pings_por_dia: dict[float, float] = config.PINGS_POR_DIA,
    hueco_entre_pings_min: dict[float, float] = config.HUECO_ENTRE_PINGS_MIN,
    permanencia_min: float = config.PERMANENCIA_MIN,
    velocidad_m_min: float = config.VELOCIDAD_M_MIN,
    ruido_espacial_A_m: float = config.RUIDO_ESPACIAL_A_M,
    dispersion_vagabundeo_m: float = config.DISPERSION_VAGABUNDEO_M,
    frac_con_cdr: float = config.FRAC_CON_CDR,
    seed: int = 0,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    rng = np.random.default_rng(seed)

    ciudad = crear_ciudad(n_paraderos, tarjetas_por_paradero, rng)
    visitas = visitas_verdaderas(ciudad, n_personas, n_dias, lugares_por_persona,
                                 actividad_por_persona, perfil_rango, perfil_horario,
                                 variacion_diaria_min, rng)
    eventos_B = observa_bip(visitas, ciudad)

    # Solo una fracción de las personas tiene CDR
    n_con_cdr = max(1, round(n_personas * frac_con_cdr))
    eventos_A = observa_cdr(visitas, ciudad, n_con_cdr, n_dias, pings_por_dia,
                            hueco_entre_pings_min, permanencia_min, velocidad_m_min,
                            ruido_espacial_A_m, dispersion_vagabundeo_m, rng)

    # Solo las personas que quedaron con eventos en las dos fuentes pueden enlazarse.
    comunes = np.array(sorted(set(eventos_A["persona"]) & set(eventos_B["persona"])))
    verdad = pd.DataFrame({"entidad_A": comunes, "entidad_B": comunes + (1 << 24)})

    return a_esquema(eventos_A, "A"), a_esquema(eventos_B, "B"), verdad
