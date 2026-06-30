# El escenario base del generador sintetico
#
# Casi todo se midio sobre el Bip y el CDR reales con validacion/anclaje.py

import pandas as pd

N_SEMILLAS = 10   # mundos por punto de cada curva del barrido


# La ciudad

PERSONAS_POR_PARADERO_REAL = 976

TARJETAS_POR_PARADERO = {
    0.0: 1, 0.01: 2, 0.05: 9, 0.10: 21, 0.25: 68, 0.50: 205,
    0.75: 549, 0.90: 1320, 0.95: 2196, 0.99: 14078,
    0.995: 37925, 0.999: 89487, 1.0: 203353,
}


# Las personas

N_PERSONAS = 60000

FRAC_CON_CDR = 0.1
FRAC_CON_CDR_REAL = 0.0066   # medido: 22.343 usuarios contra 3.404.382 tarjetas

LUGARES_POR_PERSONA = (
    629277, 908252, 609968, 448405, 305345, 199663, 125577, 75954, 44583, 25196,
    14235, 7845, 4328, 2429, 1324, 758, 464, 232, 193, 93, 78, 49, 39, 24, 19,
    13, 10, 11, 2, 5, 2, 2, 3, 0, 1, 2, 0, 0, 0, 1,
)

ACTIVIDAD_POR_PERSONA = (
    526549, 607356, 341410, 344367, 234536, 233632, 183997, 215702, 157200, 145161,
    108064, 88298, 63330, 47600, 33177, 23255, 15971, 10861, 7236, 5148, 3290, 2331,
    1556, 1150, 834, 587, 406, 295, 218, 189, 124, 124, 70, 75, 38, 39, 28, 25, 22,
    24, 12, 9, 16, 11, 9, 6, 6, 4, 4, 3, 5, 3, 2, 1, 1, 1, 2, 0, 0, 12,
)

LUGARES_POR_PERSONA_MEDIA = (sum(i * n for i, n in enumerate(LUGARES_POR_PERSONA, start=1))
                             / sum(LUGARES_POR_PERSONA))
N_PARADEROS = round(N_PERSONAS * LUGARES_POR_PERSONA_MEDIA / PERSONAS_POR_PARADERO_REAL)


# La rutina

N_DIAS = 7        
DIAS_MEDIDOS = 7 

PERFIL_RANGO = (3, 2, 1)

PERFIL_HORARIO = {
    5: 0.2, 6: 2.1, 7: 4.8, 8: 5.3, 9: 4.1, 10: 4.0, 11: 4.8, 12: 5.7,
    13: 6.5, 14: 6.3, 15: 6.3, 16: 7.4, 17: 10.0, 18: 11.5, 19: 8.1,
    20: 6.6, 21: 4.2, 22: 2.1, 23: 0.1,
}

VARIACION_DIARIA_MIN = 9.7   

# Lo que ve cada fuente

PINGS_POR_DIA = {0.0: 5, 0.10: 8, 0.25: 15, 0.50: 33, 0.75: 68, 0.90: 129, 0.99: 323,
                 0.995: 392, 0.999: 600, 1.0: 1810}

HUECO_ENTRE_PINGS_MIN = {0.0: 0.0, 0.10: 0.05, 0.25: 0.25, 0.50: 0.93, 0.75: 12.7,
                         0.90: 29.9, 0.99: 164.8, 0.995: 232.8, 0.999: 420.0, 1.0: 944.6}


PERMANENCIA_MIN = 15

VELOCIDAD_M_MIN = 80

RUIDO_ESPACIAL_A_M = 300

DISPERSION_VAGABUNDEO_M = 2000


# Donde y cuando ocurre el mundo
LAT_MIN, LAT_MAX = -33.4946, -33.4554
LON_MIN, LON_MAX = -70.6735, -70.6265
HORA_INICIO, HORA_FIN = 6, 24              # casi todos los pings del CDR ocurren en este rango
FECHA_BASE = pd.Timestamp("2024-03-04")    # un lunes cualquiera
