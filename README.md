# Framework para evaluar la factibilidad de re-identificación de personas entre trazas digitales de movilidad: aplicación al cruce de telefonía móvil (CDR) y transporte público (Bip) en Santiago

Trabajo de título de Ingeniería Civil en Computación, Universidad de Chile (FCFM).
Profesor guía: Eduardo Graells-Garrido.

## De qué se trata

Moverse por la ciudad deja rastro en varios lados a la vez. El celular queda registrado en las
antenas a las que se conecta (los datos CDR) y la tarjeta Bip queda registrada cada vez que se
valida en un bus o en el metro. Para proteger la identidad, estos datos se entregan seudonimizados: en vez del nombre de la persona, se utiliza un código.

Seudonimizar no es lo mismo que anonimizar. Tapar la columna de identidad no borra a la
persona, porque sus registros siguen teniendo patrones que pueden ser únicos. Con
información suficiente, ese código se puede volver a asociar a alguien.

Este trabajo busca medir hasta qué punto es posible identificar esos registros al cruzar ambas fuentes, y cómo se distribuye este riesgo dentro de la ciudad.

La idea: si un celular y una tarjeta aparecen repetidamente en el mismo lugar y a la misma hora, es posible que pertenezcan a la misma persona.

## Cómo funciona

El framework recibe dos fuentes de eventos y devuelve qué fracción de la población de una
quedó enlazada con la otra. Son tres capas más una aplicación:

1. **Adaptar.** Cada fuente se traduce a cinco columnas comunes:
   `entidad_id, lat, lon, timestamp, fuente`. 
2. **Enlazar.** Se buscan las co-ocurrencias, osea los pares de eventos que ocurrieron el mismo día, a menos de `RADIO_METROS` y con menos de `VENTANA_MINUTOS` de diferencia. Después se cuenta
   en cuántos días distintos coincidió cada pareja.
3. **Decidir.** Se acepta una pareja como enlace si coincidió al menos `MIN_DIAS_COINCIDENCIA`
   días, si es la favorita sin empate de las dos, y si la elección es recíproca. Con eso se
   calcula la tasa de enlace de la población.
4. **Aplicación.** La misma tasa, pero dentro de un grupo. Opcional: solo pasa si se entrega
   un atributo que etiquete a cada entidad.

Las capas 2 y 3 y la aplicación no saben de dónde vienen los datos. Este repositorio las corrió sobre CDR y
Bip, pero sirve igual para cualquier par de fuentes que registren movilidad (quíen, dónde y cuándo).

## Usarlo con otras fuentes

### 1. Escribir un adaptador por fuente

Hay que escribir una función sin argumentos que devuelve los eventos en el esquema común. `a_eventos` hace la
traducción: le dices qué columna de tu tabla cruda corresponden a las requeridas por la función (fuente, col_entidad, col_lat, col_lon, col_timestamp)

```python
import pandas as pd
from reid.fuentes.esquema import a_eventos

def cargar_wifi():
    crudo = pd.read_csv("data/wifi.csv")
    return a_eventos(crudo, 
                     fuente="wifi", col_entidad="n_mac",
                     col_lat="latitud", col_lon="longitud", col_timestamp="visto_en")

def cargar_bicis():
    crudo = pd.read_parquet("data/bicis.parquet")
    return a_eventos(crudo, 
                     fuente="bicis", col_entidad="n_socio",
                     col_lat="lat_est", col_lon="lon_est", col_timestamp="hora_retiro")
```

La limpieza propia de la fuente va acá adentro, antes de `a_eventos`. Para el Bip, por ejemplo,
hubo que construir un diccionario de paraderos y convertir los archivos crudos: eso vive en
`reid/fuentes/bip.py` y `reid/fuentes/paraderos.py`, junto al adaptador que lo usa.


**Condición:** `entidad_id` es la columna que dice de quién es cada evento, osea el código seudonimizado que usa esa fuente, y este tiene que ser un entero que quepa en 32 bits, o sea entre 0 y 4.294.967.295. 


### 2. Ajusta los tres parámetros del método

En `reid/config.py`. Dependen de tus fuentes, no del framework:

```python
RADIO_METROS = 500           # cuán cerca en el espacio para considerar que coinciden
VENTANA_MINUTOS = 3          # cuán cerca en el tiempo
MIN_DIAS_COINCIDENCIA = 3    # en cuántos días distintos tienen que coincidir
```

Los valores de arriba son los del caso CDR-Bip.

### 3. Llama al framework

```python
from reid import pipeline
from reid.config import RESULTADOS

pipeline.correr(cargar_A=cargar_wifi,
                cargar_B=cargar_bicis,
                resultados_en=RESULTADOS / "mi_caso")
```

Eso deja en `resultados/mi_caso/` la tasa de enlace, los enlaces aceptados y un `resumen.json`
con los números de la corrida.

### 4. Opcional: repartir la tasa por grupo

El framework entrega una tasa para toda la población. Si además se quiere saber la tasa por grupo (comuna, edad, lo que sea), hay que pasarle una función que reciba los eventos de la fuente A y devuelva
`{nombre_del_archivo: atributo}`, donde el atributo es una `pd.Series` indexada por `entidad_id`
con la etiqueta de cada uno. Las que queden con `NaN` no entran a ningún grupo.

```python
def mis_atributos(eventos_wifi):
    entidades = pd.Index(eventos_wifi["entidad_id"].unique())
    facultad = pd.Series(["norte" if e < 150 else "sur" for e in entidades],
                         index=entidades, name="facultad")
    return {"tasa_facultad": facultad}

pipeline.correr(cargar_A=cargar_wifi, cargar_B=cargar_bicis,
                resultados_en=RESULTADOS / "mi_caso", atributos=mis_atributos)
```

Eso escribe `resultados/mi_caso/tasa_facultad.csv` con una fila por grupo. Puedes devolver
varios atributos y sale un archivo por cada uno. Los tres del caso CDR-Bip están en
`reid/aplicacion/atributos.py`: comuna del hogar, hexágono H3 y cuartil de actividad.

## Correr el caso CDR-Bip

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .          # instala el paquete reid y sus dependencias (ver pyproject.toml)

python correr.py datos    # prepara los paraderos y convierte el Bip a parquet (una sola vez)
python correr.py          # el caso, los análisis y las figuras, en orden
```

Cada día procesado queda guardado en `trabajo/`.

Cada etapa se puede correr sola (`python correr.py figuras`), pero sin argumentos van las tres
seguidas, que es lo que evita dejar en `resultados/` números de dos corridas distintas.

## Cómo está organizado

```
correr.py       # el caso de estudio: adaptadores, atributos y las etapas
reid/           # el framework
analisis/       # los números del caso que no salen del pipeline (Moran, H3, correlaciones)
graficos/       # dibuja, leyendo solo de resultados/
data/           # los insumos, no se pueden regenerar
trabajo/        # intermedios pesados, se pueden borrar y volver a generar
resultados/     # los números finales, los que se citan
figuras/        # las imágenes que produce graficos/
```

```
reid/
├── config.py                 # Los tres parámetros del método y las rutas
├── config_caso.py            # Rutas y filtros del caso CDR-Bip
├── fuentes/                  # Capa 1: cargar cada fuente al esquema común
│   ├── esquema.py            # Esquema canónico (entidad_id, lat, lon, timestamp, fuente)
│   ├── cdr.py                # Adaptador del CDR
│   ├── bip.py                # Adaptador del Bip
│   └── paraderos.py          # Diccionario de paraderos
├── enlace/                   # Capa 2: enlazar fuentes espacio-temporalmente
│   ├── espaciotemporal.py    # Coincidencias por cercanía (BallTree, 500 m, ±3 min)
│   └── agregacion.py         # En cuántos días coincidió cada pareja
├── decision/                 # Capa 3: decidir qué parejas se aceptan y medir la tasa
│   ├── enlace_mutuo.py       # Enlace mutuo
│   └── tasa.py               # Qué fracción de una población quedó enlazada
├── aplicacion/               # Reparte la tasa entre grupos
│   ├── por_grupo.py          # La tasa dentro de cada grupo, dado un atributo
│   ├── atributos.py          # Los atributos del caso: comuna, hexágono H3, cuartil
│   └── hogar.py              # Estima el hogar de cada persona
└── pipeline.py               # Corre las cuatro etapas de punta a punta
```

## Resultados del caso CDR-Bip

- El método principal es el enlace mutuo (uno-a-uno): un celular y una tarjeta se enlazan solo si
  cada uno es la mejor opción del otro. Re-identifica un 7,64% bruto: 1.706 de los 22.343 usuarios
  CDR, u 8,41% de los 20.282 que tuvieron actividad en la semana del Bip. Es un mínimo: con más
  días de datos el número subiría.
- Una coincidencia aislada no identifica a nadie. Lo que sí identifica es coincidir con una entidad en varios días distintos, ya que hay repetición de una rutina.
- La limitación principal es la ventana de 7 días de Bip, ya que no se alcanza a ver una rutina semanal si vemos solo 1 semana.
- El riesgo no se reparte parejo: va de 0,5% a 15,6% entre comunas, y las comunas vecinas se
  parecen entre sí (Moran's I = +0,543, p = 0,001; `figuras/moran_lisa_riesgo.png`, mapa en
  `figuras/mapa_riesgo_comuna.png`).
- No se puede saber **por qué** es desigual con las herramientas que tenemos. Ninguna de las
  cuatro variables comunales disponibles explica la diferencia: población total (Spearman +0,34),
  usuarios CDR (+0,22), cobertura por habitante (−0,19) y pobreza (+0,02)
  (`resultados/caso/correlaciones_comuna.csv`). Y tampoco se pueden separar entre ellas: las
  comunas con más población son las mismas que tienen más usuarios CDR (r = 0,87). Con 44
  comunas y variables tan entrelazadas, la desigualdad queda descrita pero no explicada.
- Al repetir el análisis sobre hexágonos H3, que son mucho más chicos que una comuna
  (`figuras/mapa_riesgo_h3.png`), el agrupamiento aparece o desaparece según cuántos usuarios se
  exija por hexágono: va de +0,25 significativo a −0,17 (`resultados/caso/sensibilidad_h3.csv`).
  O sea que el resultado depende de cómo se dibujen las unidades: el problema de la unidad areal
  modificable (MAUP). La conclusión se sostiene a nivel de comuna, pero los datos no alcanzan
  para bajar de esa escala.
- A nivel de persona el mecanismo sí aparece claro: mientras más datos hay de alguien en el CDR,
  más riesgo. Del grupo con menos datos al grupo con más, la re-identificación salta de 1,1% a
  14,1%, unas 13 veces.

## Datos requeridos (no incluidos en el repositorio)

```
data/
├── telefonia_por_usuario/    # CDR en Parquet (CENIA, noviembre 2023, RM)
├── viajes/                   # Bip: los .csv.gz originales (DTPM, 7 días)
├── gtfs/                     # GTFS RED + consolidado DTPM de paraderos
├── comunas_chile.json.zip    # Geometrías comunales (GADM)
└── pobreza_comunal.xlsx      # Tasa de pobreza por comuna (SAE 2022)
```

## Referencias

- De Montjoye, Y.-A., et al. (2013). Unique in the Crowd: The privacy bounds of human mobility.
  Scientific Reports.
- Zang, H., y Bolot, J. (2011). Anonymization of location data does not work.
- Riederer, C., et al. (2016). Linking Users Across Domains with Location Data. WWW.
- Farzanehfar, A., Houssiau, F., y de Montjoye, Y.-A. (2021). The risk of re-identification
  remains high even in country-scale location datasets. Cell Patterns.
- Wesolowski, A., et al. (2013). The impact of biases in mobile phone ownership on estimates of
  human mobility. Journal of the Royal Society Interface.
- Ricciato, F., et al. (2017). Beyond the single-operator, CDR-only paradigm. Pervasive and
  Mobile Computing.
- Ahas, R., et al. (2010). Using mobile positioning data to model locations meaningful to users
  of mobile phones. Journal of Urban Technology.
- Ley 21.719 (2024). Ley que regula la protección y el tratamiento de datos personales, Chile.
