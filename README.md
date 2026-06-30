# Framework para evaluar la factibilidad de re-identificación de personas entre trazas digitales de movilidad: aplicación al cruce de telefonía móvil (CDR) y transporte público (Bip) en Santiago

Trabajo de título de Ingeniería Civil en Computación, Universidad de Chile (FCFM).
Profesor guía: Eduardo Graells-Garrido.

## De qué se trata

Una persona al moverse por la ciudad deja rastros de distintas formas. Con un celular con plan telefónico, este queda registrado en las antenas a las que se conecta (los datos CDR), y si se usa el transporte público queda registrada la tarjeta Bip cada vez que se valida en un bus o metro. Estos datos se entregan seudonimizados, osea que en vez del nombre o identificador de una persona, se utiliza un código que no revela la identidad directamente.

Seudonimizar no es lo mismo que anonimizar. Esconder la columna de identidad no borra a la
persona, ya que sus registros siguen teniendo patrones que podrían ser únicos. Con
información suficiente, ese código se puede volver a asociar a alguien.

Este trabajo busca medir hasta qué punto es posible identificar esos registros al cruzar ambas fuentes, y cómo se distribuye este riesgo dentro de la ciudad.

La idea: si un celular y una tarjeta aparecen repetidamente en el mismo lugar y a la misma hora, es posible que pertenezcan a la misma persona.

## Cómo funciona

El framework recibe dos fuentes de eventos y devuelve qué fracción de la población de una
quedó enlazada con la otra. Son tres capas más una aplicación:

1. **Adaptar.** Cada fuente se traduce a cinco columnas comunes:
   `entidad_id, lat, lon, timestamp, fuente`. 
2. **Enlazar.** Se buscan las co-ocurrencias, osea los pares de eventos que ocurrieron el mismo día, a menos de `RADIO_METROS` y con menos de `VENTANA_MINUTOS` de diferencia. Después se cuenta
   en cuántos días distintos coincidió cada par.
3. **Decidir.** Se acepta una pareja como enlace si coincidió al menos `MIN_DIAS_COINCIDENCIA`
   días, si es la favorita sin empate de las dos, y si la elección es recíproca. Con eso se
   calcula la tasa de enlace de la población.
4. **Aplicación.** La misma tasa, pero dentro de un grupo. Opcional: solo pasa si se entrega
   un atributo que etiquete a cada entidad.

Las capas 2 y 3 y la aplicación no saben de dónde vienen los datos. Este trabajo las corrió sobre CDR y
Bip, pero sirve igual para cualquier par de fuentes que registren movilidad (quíen, dónde y cuándo).

## Instalación

El trabajo se ejecuta con [uv](https://docs.astral.sh/uv/getting-started/installation/), que fija
la versión exacta de cada dependencia en `uv.lock`.

```bash
git clone <este repositorio> 
uv sync                     
```

## Usarlo con otras fuentes

### 1. Un adaptador por fuente

Una función sin argumentos que devuelve los eventos en el esquema común. `a_eventos` hace la
traducción: recibe qué columna de la tabla cruda corresponde a cada una de las cinco que necesita el framework.

**Dónde:** un archivo por fuente en `reid/fuentes/`.

```python
# reid/fuentes/wifi.py
import pandas as pd
from .esquema import a_eventos

def cargar_eventos() -> pd.DataFrame:
    crudo = pd.read_csv("data/wifi.csv")
    return a_eventos(crudo, fuente="wifi", col_entidad="n_mac",
                     col_lat="latitud", col_lon="longitud", col_timestamp="visto_en")
```

La limpieza propia de la fuente va adentro, antes de `a_eventos`. Para el Bip, por ejemplo, hubo
que construir un diccionario de paraderos y convertir los archivos crudos.

**Condición:** `entidad_id` es el código seudonimizado de la fuente y tiene que ser un entero de 32 bits, osea
entre 0 y 4.294.967.295, ya que el enlace empaqueta ambos id en un numero de 64 bits.

### 2. Los tres parámetros del método

**Dónde:** `reid/config.py`.

```python
RADIO_METROS = 200           # cuán cerca en el espacio para considerar que coinciden
VENTANA_MINUTOS = 5          # cuán cerca en el tiempo
MIN_DIAS_COINCIDENCIA = 3    # en cuántos días distintos tienen que coincidir
```

Los de arriba son los del caso CDR-Bip y dependen de la precisión de tus fuentes.


### 3. Un script que llame al framework

**Dónde:** un archivo en la raíz, como `correr.py`.

```python
# mi_caso.py
from reid import pipeline
from reid.config import RESULTADOS
from reid.fuentes.wifi import cargar_eventos as cargar_wifi
from reid.fuentes.bicis import cargar_eventos as cargar_bicis

pipeline.correr(cargar_A=cargar_wifi, cargar_B=cargar_bicis,
                resultados_en=RESULTADOS / "mi_caso")
```

Y se corre desde la terminal:

```bash
python mi_caso.py
```

Eso deja en `resultados/mi_caso/` la tasa de enlace, los enlaces aceptados y un `resumen.json`.

### 4. Opcional: la tasa dentro de cada grupo

Lo mismo de arriba, pasándole además un atributo. Un atributo es una función que recibe los
eventos de la fuente A y devuelve `{nombre_del_archivo: etiquetas}`, donde `etiquetas` es una
`pd.Series` indexada por `entidad_id`. Las que queden en `NaN` no entran a ningún grupo.

**Dónde:**  en `reid/aplicacion/atributos.py`.

```python
# mi_caso.py
def mis_atributos(eventos_wifi):
    entidades = pd.Index(eventos_wifi["entidad_id"].unique())
    facultad = pd.Series(["norte" if e < 150 else "sur" for e in entidades],
                         index=entidades, name="facultad")
    return {"tasa_facultad": facultad}

pipeline.correr(cargar_A=cargar_wifi, cargar_B=cargar_bicis,
                resultados_en=RESULTADOS / "mi_caso", atributos=mis_atributos)
```

Eso agrega `resultados/mi_caso/tasa_facultad.csv`, con una fila por grupo. Puedes devolver varios
atributos y sale un archivo por cada uno. Los del caso CDR-Bip están en
`reid/aplicacion/atributos.py`: comuna del hogar, hexágono H3 y cuartil de actividad.


## Correr el caso CDR-Bip

`correr.py` es exactamente el script del paso 3: junta los adaptadores del CDR y del Bip, los
atributos de comuna y actividad, y llama a `pipeline.correr()`. Además encadena los análisis y
las figuras, que ya no son framework sino interpretación.

```bash
python correr.py datos    # prepara los paraderos y convierte el Bip a parquet (una sola vez)
python correr.py          # el caso, los análisis y las figuras, en orden
```

Cada día procesado queda guardado en `trabajo/`, así que una corrida interrumpida se retoma. Cada
etapa se puede correr sola (`python correr.py figuras`), pero sin argumentos van las tres seguidas.


## Validar el framework

En el caso CDR-Bip nadie sabe qué tarjeta es de qué celular, así que no se puede medir si un
enlace acertó. La validación evalúa eso con dos mundos donde la respuesta sí se conoce:

- **Sintético**: una ciudad inventada, donde en cierta medida se buscaba replicar los datos CDR y Bip.
- **Semi-sintético**: el CDR real partido en dos mitades de eventos, cada una con su propio seudónimo. 

En esos dos mundos se miden precisión y recall directamente. En el caso real no se puede, y ahí
entra el **test del azar**.

### El test del azar

Sirve para puntuar una configuración cuando no hay respuesta correcta. Se barajan las identidades
de una fuente dentro de cada grupo de misma ubicación, misma hora y mismo día, y se corre el mismo
enlace encima. Lo que salga son enlaces que produce la casualidad, y la
diferencia contra lo observado es la puntuación.

En el caso CDR-Bip, con los parámetros elegidos: 1.660 enlaces observados contra 1.403 de las
barajadas, o sea que el azar explica el 84,5 % del volumen y ninguna de las 30 barajadas alcanzó
el resultado real.

En el mundo sintético y en el semi-sintético se pueden
calcular las dos puntuaciones a la vez, la del azar y el F1, y ver si eligen los mismos
parámetros. Eso es lo que permite usar el test del azar en el caso real, donde el F1 no existe.

### Correrlo

```bash
python validar.py anclaje                    # mide sobre el Bip y el CDR los parámetros del generador
python validar.py barrido                    # cómo cambia el desempeño al mover cada condición
python validar.py optimalidad sintetico      # elige radio, ventana y umbral en el mundo inventado
python validar.py optimalidad semisintetico  # lo mismo sobre el CDR partido en dos
python validar.py optimalidad caso           # lo mismo sobre el cruce CDR-Bip
python validar.py azar                       # el test del azar sobre la población completa
python -m graficos.barrido                   # dibuja las doce curvas del barrido
```

Cada etapa escribe un csv en `resultados/validacion/`. 

| etapa | qué escribe | 
|---|---|
| `anclaje` | `anclaje.json`, que se copia a mano a `validacion/config.py` | 
| `barrido` | un `barrido_<parámetro>.csv` por curva | 
| `optimalidad sintetico` | `optimalidad_sintetico.csv` | 
| `optimalidad semisintetico` | `optimalidad_semisintetico.csv` | 
| `optimalidad caso` | `optimalidad_caso.csv` | 
| `azar` | `azar_por_umbral_dias.csv` | 


### Por qué se parte el CDR y no el Bip

Elegir los parámetros con los mismos datos con que después se reporta el resultado sería hacer
trampa. Por eso `optimalidad caso` parte **los usuarios del CDR** en dos mitades que no comparten
ninguna persona: elige los parámetros en una y comprueba en la otra. 

Los parámetros se eligen mirando cuántos enlaces sobreviven a la competencia, y la competencia la pone el Bip: cuánta gente pasa por el mismo
paradero a la misma hora. Con la mitad de las tarjetas habría la mitad de competencia, así que se
estaría eligiendo un radio para una ciudad que no existe.


### Usarla con otras fuentes

No hay que implementar nada nuevo. Los adaptadores que escribiste para el framework son los
mismos que usa la validación: recibe tablas de eventos en el esquema común y no le importa de
dónde salieron. Lo único que hay que escribir es un script que llame a tres funciones, igual que
`validar.py` hace para el CDR y el Bip.

```python
# validar_mi_caso.py
from reid.decision.enlace_mutuo import enlace_mutuo
from reid.fuentes.wifi import cargar_eventos as cargar_wifi
from reid.fuentes.bicis import cargar_eventos as cargar_bicis
from validacion.azar import test_de_azar
from validacion.enlace import enlazar
from validacion.metricas import evaluar
from validacion.optimalidad import calibrar, elegidos
from validacion.semisintetico import partir_en_dos

wifi, bicis = cargar_wifi(), cargar_bicis()

# 1. Elegir el radio, la ventana y el umbral de días
tabla = calibrar(wifi, bicis)
print(elegidos(tabla))      

# 2. Cuánto del resultado explica la casualidad
print(test_de_azar(wifi, bicis, umbrales=[1, 2, 3, 4, 5]))

# 3. Opcional: precisión y recall, partiendo una fuente en dos
A, B, verdad = partir_en_dos(wifi, seed=0)
pares = enlazar(A, B, radio_m=200, ventana_min=5)
print(evaluar(enlace_mutuo(pares, min_dias=3), verdad))
```

**Lo que no sirve tal cual** es el generador sintético (`validacion/sintetico.py`): sus valores
por defecto están medidos sobre el Bip y el CDR, así que describe esta ciudad específica. Para
usarlo con otras fuentes habría que medir de nuevo esos valores, que es lo que hace
`validacion/anclaje.py`.

## Cómo está organizado

```
correr.py       # el caso de estudio: adaptadores, atributos y las etapas
validar.py      # la validación, instanciada sobre las fuentes del caso
reid/           # el framework
analisis/       # números de análisis del caso 
validacion/     # comprueba que el framework funciona y bajo qué condiciones
graficos/       # dibuja, leyendo solo de resultados/
data/           # los insumos, no se pueden regenerar
trabajo/        # intermedios pesados, se pueden borrar y volver a generar
resultados/     # los números finales
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
│   ├── espaciotemporal.py    # Coincidencias por cercanía, con un BallTree por franja
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

Con radio 200 m, ventana 5 min y mínimo 3 días, elegidos con el procedimiento de calibración.

- El método principal es el enlace mutuo (uno-a-uno): un celular y una tarjeta se enlazan solo si
  cada uno es la mejor opción del otro. Re-identifica un **7,43 % bruto: 1.660 de los 22.343
  usuarios CDR**, u 8,18 % de los 20.282 que tuvieron actividad en la semana del Bip. Es un
  mínimo: al acumular días la curva todavía sube en el séptimo
  (`resultados/validacion/sensibilidad_dias.csv`).
- **El azar explica el 84,5 % del volumen.** Barajando las identidades salen 1.403 enlaces contra
  los 1.660 observados, y ninguna de las 30 barajadas alcanzó el resultado real
  (`resultados/validacion/azar_por_umbral_dias.csv`). O sea que hay señal, pero no se puede saber
  cuáles de los 1.660 pares son correctos.
- El riesgo no se reparte parejo: va de 0 % a 15,7 % entre las 44 comunas con al menos 100
  usuarios, con mediana 8,0 %, y las comunas vecinas se parecen entre sí (Moran's I = +0,524,
  p = 0,001; `figuras/moran_lisa_riesgo.png` y `figuras/mapa_riesgo_comuna.png`).
- El mismo agrupamiento aparece también a escala de hexágono, mucho más chica que una comuna:
  +0,113 con p = 0,028 (`figuras/mapa_riesgo_h3.png`).
  El índice baja al exigir más usuarios por hexágono: +0,32 con 20, +0,11 con 50, +0,07 con 100
  (`resultados/caso/sensibilidad_h3.csv`). La razón es que ese filtro deja fuera los hexágonos con
  poca gente, que son los de la periferia. Quedan solo los del centro, que se parecen todos entre
  sí, y sin periferia no queda contraste que medir.

- Se probó si esa desigualdad se explica por alguna característica de la comuna. De las cuatro
  disponibles, dos correlacionan con la tasa y dos no
  (`resultados/caso/correlaciones_comuna.csv`):

  | variable de la comuna | correlación con la tasa | ¿significativa? |
  |---|---|---|
  | población total | +0,59 | sí |
  | usuarios CDR observados | +0,54 | sí |
  | penetración del operador | −0,01 | no |
  | pobreza | −0,25 | no |

  O sea que las comunas más grandes se enlazan más. Pero eso no explica gran cosa, porque las
  dos variables que correlacionan son casi la misma: las comunas con más población son las que
  tienen más usuarios CDR (r = 0,87 entre ellas). Con solo 44 comunas no hay forma de separar cuál
  de las dos manda. La desigualdad queda descrita y asociada al tamaño, pero no explicada.
- A nivel de persona el mecanismo aparece claro: mientras más datos hay de alguien en el CDR, más
  riesgo. Del cuartil con menos actividad al de más, la tasa salta de **0,7 % a 15,8 %**.

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
