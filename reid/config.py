from pathlib import Path

ROOT = Path(__file__).parent.parent

DATA       = ROOT / "data"
TRABAJO    = ROOT / "trabajo"
RESULTADOS = ROOT / "resultados"
FIGURAS    = ROOT / "figuras"     # las imagenes que salen de graficos/

RES_CASO        = RESULTADOS / "caso"
RES_VALIDACION  = RESULTADOS / "validacion"
RES_CALIBRACION = RESULTADOS / "calibracion"

# Los tres parámetros del método de enlace
RADIO_METROS = 200
VENTANA_MINUTOS = 5
MIN_DIAS_COINCIDENCIA = 3


