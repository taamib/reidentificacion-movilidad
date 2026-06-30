# Rutas y filtros del caso de estudio: telefonía (CDR) y transporte público (Bip) de Santiago.

from .config import DATA, TRABAJO

# CDR
TELEFONIA       = DATA / "telefonia_por_usuario"
MIN_PINGS_DIA   = 5     # mínimo de pings por día para considerar al usuario
RM_FRACCION_MIN = 0.80  # mínima fracción de pings dentro de la RM para conservar al usuario

# Rectángulo de la Región Metropolitana
LAT_MIN_RM, LAT_MAX_RM = -34.3, -33.0
LON_MIN_RM, LON_MAX_RM = -71.1, -70.2

# Viajes Bip
VIAJES     = DATA / "viajes"              # los .csv.gz entregados
VIAJES_BIP = TRABAJO / "viajes_bip"       # los mismos ya convertidos, se regeneran

COLUMNAS_VIAJES_ELIMINAR = [
    "Unnamed: 100",
    "mediahora_inicio_viaje", "mediahora_fin_viaje",
    "mediahora_bajada_1", "mediahora_bajada_2",
    "mediahora_bajada_3", "mediahora_bajada_4",
    "mediahora_inicio_viaje_hora", "mediahora_fin_viaje_hora",
    "op_1era_etapa", "op_2da_etapa", "op_3era_etapa", "op_4ta_etapa",
    "tv3", "tc3", "tv4", "tviaje", "tviaje2", "egreso",
    "proposito", "tv1", "tc1", "te1", "tv2", "tc2", "te2", "te3",
]

# GTFS y registro de paradas
GTFS = DATA / "gtfs"
# Registro de paradas del DTPM
DTPM       = GTFS / "paradas" / "2023-12-16_consolidado_Registro-Paradas_anual.xlsx"
DTPM_HOJA  = "28Oct2023 al 10Nov2023"
STOPS      = GTFS / "stops.txt"
TRIPS      = GTFS / "trips.txt"
STOP_TIMES = GTFS / "stop_times.txt"
PARADEROS  = GTFS / "paradas" / "paraderos_coords.csv"

# Datos comunales, para el atributo territorial y el análisis del caso
COMUNAS_GEOJSON = DATA / "comunas_chile.json.zip"  # bajado de GADM (todas las comunas Chile)
POBREZA_COMUNAL = DATA / "pobreza_comunal.xlsx"    # población y tasa de pobreza (SAE 2022)

# Mínimo de entidades para que la tasa de un grupo sea estable
MIN_ENTIDADES_GRUPO = 100
