# Capítulo 2 — Cinco capas y una sola verdad

> Borrador. Fuente: código de la v1.3 (backend/main.py, backend/lab_env.py, backend/telemetry_api.py,
> vertex-forensic-mcp/server.py) y logs/bitacora.md (6 de noviembre de 2026, entradas de las 14:34 y 14:42).

Antes de medir nada, hay que saber dónde vive cada pieza y qué le toca hacer. Vertex Forensic Lab
tiene cinco capas, y cada una tiene una responsabilidad que no comparte con ninguna otra. Este
capítulo las recorre de fuera hacia dentro, en el orden en que las atraviesa una petición hostil.

Al final del capítulo hay una sexta pieza que no es una capa, sino una regla. Es la que más me
costó aprender en este proyecto, y la que más errores evitó después.

## El mapa

```
  atacante (Parrot)                          operador (localhost)
          │                                           │
          ▼                                           ▼
  ┌──────────────────────────────────────────────────────────────┐
  │ 1. GATEWAY FASTAPI  :8000                                     │
  │    middleware forense  →  señuelos  →  superficie de mando   │
  └───────────┬──────────────────────────────────┬───────────────┘
              │ evidencia                        │ solo loopback
              ▼                                  ▼
  ┌──────────────────────┐            ┌──────────────────────────┐
  │ 2. BÓVEDA DUCKDB     │◄──────────►│ 3. PERITO HÍBRIDO        │
  │    4 tablas          │            │    Python + modelo local │
  └──────────┬───────────┘            └──────────────────────────┘
             │
     ┌───────┴────────────────┐
     ▼                        ▼
  ┌──────────────────┐   ┌──────────────────────┐
  │ 4. HUD ANGULAR   │   │ 5. SERVIDOR MCP      │
  │    :4200         │   │    stdio             │
  └──────────────────┘   └──────────────────────┘
```

## Capa 1: el gateway

El gateway es una aplicación FastAPI que escucha en el puerto 8000. Todo el tráfico entra por
aquí, y lo primero que encuentra es un **middleware forense**: una función que se ejecuta antes de
cada petición, sin importar a qué ruta vaya.

El middleware hace cuatro cosas, en este orden:

1. Calcula la **huella de sesión** del cliente a partir de su IP, su User-Agent y la cabecera
   `X-Swarm-Node`.
2. Mide el **tiempo desde la petición anterior** de esa misma huella y la **entropía** de lo que
   envía.
3. Comprueba si la petición trae un **Canary Token** y si su contenido parece una inyección.
4. Aplica el **tarpit** si la sesión acumula sospechas, y guarda la evidencia en la bóveda.

Solo después de todo eso la petición llega a su ruta. Detrás del middleware hay tres grupos de
rutas:

- **Los señuelos**, que imitan una API interna mal protegida: `/api/v1/system/config`, que entrega
  el token trampa, y `/api/v2/internal/vault`, que finge ser una bóveda de claves vulnerable a
  inyección SQL.
- **La telemetría** (`/api/telemetry/state`), que alimenta el panel.
- **Las acciones** (`/api/actions/*`): ejecutar el perito, bloquear una IP y exportar el acta.

Los dos últimos grupos forman la **superficie de mando**. Son las rutas con las que el operador
controla el laboratorio, y por eso son las más peligrosas si caen en las manos equivocadas. El
capítulo 8 entero trata de protegerlas.

## Capa 2: la bóveda

Toda la evidencia vive en un único archivo DuckDB: `forensic_vault/telemetry.duckdb`. Elegí
DuckDB por tres razones. Es una base de datos embebida, sin servidor que instalar ni puerto que
abrir. Es columnar, lo que hace muy rápidas las consultas de agregación que necesita el perito, como
medias, medianas o máximos por sesión. Y es un solo archivo, que se puede copiar, sellar con un hash
y archivar como prueba.

La bóveda tiene cuatro tablas:

| Tabla | Una fila por… | Para qué sirve |
|---|---|---|
| `forensic_evidence` | cada petición | La telemetría cruda: huella, IP, ruta, entropía, Δt, tarpit y etiquetas |
| `swarm_lineage` | cada uso de un Canary Token | El linaje: qué Scout recogió el token y qué Exploit lo usó, y cuánto tardó |
| `forensic_verdicts` | cada sesión peritada | El veredicto, la certeza y el dictamen en JSON |
| `soar_actions` | cada sesión contenida | La regla de firewall, su estado y el motivo |

El apéndice C tiene el esquema completo, columna por columna.

## Capa 3: el perito

El perito es un script de Python, `forensic_coroner_llm.py`, que lee la bóveda, agrupa las
peticiones por huella y decide qué es cada sesión: `AUTONOMOUS_AI_AGENT` o `LEGACY_SCANNER`.

Lo llamo **híbrido** porque tiene dos partes que hacen trabajos muy distintos. La parte
determinista, escrita en Python, evalúa indicadores que se pueden comprobar: ¿esta huella usó un
token emitido a otra? ¿Su entropía supera el umbral? ¿Su User-Agent declara un framework de agentes?
Esa parte **decide**. La segunda parte es un modelo de lenguaje local, `vertex-core-sec-turn`,
servido por LM Studio, que redacta un comentario sobre la sesión. Esa parte **no decide nada**, y
el capítulo 6 explica por qué tuvo que ser así.

El perito no corre todo el tiempo. Se ejecuta cuando el operador pulsa un botón en el panel, o
desde la línea de comandos. El gateway lo lanza como un **proceso aparte**, lo que tiene una ventaja
práctica que aproveché varias veces durante las pruebas: si cambias el código del perito, el cambio
entra en la siguiente ejecución sin reiniciar el gateway.

## Capa 4: el HUD

El HUD (por *head-up display*) es el panel del operador: una aplicación Angular 19 que se abre en
`http://localhost:4200`. Cada 2,5 segundos le pide la telemetría al gateway y dibuja:

- el **panel de linaje**, con cada transferencia Scout → Exploit y su tiempo de tránsito;
- una **tarjeta por sesión**, con su IP, su número de peticiones, su cadencia, su entropía máxima,
  su veredicto y una pequeña gráfica de sus tiempos;
- tres **botones de acción**: ejecutar el perito, exportar el acta y, en cada tarjeta, aislar el
  host.

El botón de aislar no dice simplemente "bloqueado". Muestra el estado real de la contención:
**FIREWALL ACTIVO** si la regla llegó a Windows Firewall, **SIMULADO (LOOPBACK)** si el objetivo era
la propia máquina, y **SOLO LÓGICO (SIN ADMIN)** si la regla se quedó en la base de datos porque el
gateway no tenía permisos. Esa diferencia parece un detalle de interfaz. No lo es: un operador que
cree haber aislado a un atacante cuando en realidad no lo hizo está peor que uno que sabe que no lo
hizo.

## Capa 5: el servidor MCP

La última capa no es para personas, sino para modelos. El servidor `vertex-forensic-mcp/server.py`
expone la bóveda mediante el **Model Context Protocol**, el estándar con el que los asistentes de IA
usan herramientas externas. Con él, un asistente como Claude Desktop o un modelo en LM Studio puede
preguntar por los últimos eventos, por los veredictos o por el linaje, e incluso pedir un bloqueo.

El servidor MCP no tiene su propia lógica de bloqueo. Usa exactamente el mismo módulo que el
gateway, y eso nos lleva a la regla del final del capítulo. El capítulo 11 lo cuenta en detalle.

## La regla: una sola verdad

Cuando revisé el proyecto antes de las pruebas con Parrot, encontré el mismo número escrito en tres
sitios con tres valores distintos. El umbral de entropía a partir del cual una petición se considera
sospechosa valía **4.2 bits** en el middleware del gateway, **4.5 bits** en el perito y **4.5 bits**
en el informe técnico. Nadie lo había decidido así. Simplemente, cada archivo tenía su propia copia,
y una de ellas se había quedado atrás.

Lo mismo pasaba con la ruta de la bóveda. El gateway la calculaba a partir de su propia carpeta, el
API de telemetría la leía de una variable de entorno, el perito tenía una lógica propia con un caso
especial para las unidades `C:` y `E:`, y el servidor MCP otra más. En Windows, ejecutando todo desde
la carpeta correcta, funcionaba. Pero al leer el código con el despliegue en Docker en mente, salía
que el gateway ignoraba la variable de entorno, calculaba una ruta en la raíz del contenedor e
intentaba crear ahí su carpeta, en un sistema de archivos montado en solo lectura. No habría llegado a
arrancar.

La lección es antigua, pero en un laboratorio forense pesa el doble: **si el mismo dato vive en tres
sitios, tarde o temprano dice tres cosas distintas.** Y cuando ese dato es un umbral que decide si
alguien es un atacante, la discrepancia termina escrita en un acta firmada.

La solución fue un módulo pequeño, `backend/lab_env.py`, que se importa antes que cualquier otro y
que es la **única** fuente de configuración del laboratorio:

```python
load_dotenv_file(LAB_ROOT / ".env")

DB_PATH = os.environ.get("DB_PATH") or str((LAB_ROOT / "forensic_vault" / "telemetry.duckdb").resolve())
os.environ["DB_PATH"] = DB_PATH
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

ENTROPY_SQLI_THRESHOLD = float(os.environ.get("VERTEX_ENTROPY_THRESHOLD", "4.5"))

CADENCE_THRESHOLD_MS = 1000.0
BURST_GAP_MS = 30000.0
```

Tres decisiones están metidas en esas líneas.

**La primera es la precedencia.** Una variable de entorno que ya existe manda siempre: así Docker
puede fijar la ruta de la bóveda a `/app/vault/telemetry.duckdb` sin que el código la pise. El
archivo `.env` solo rellena las variables que falten. Y si no hay nada, se usa la ruta por defecto
dentro del proyecto.

**La segunda es que el cargador de `.env` está escrito a mano**, en unas pocas líneas, en lugar de
añadir una dependencia. En un laboratorio que se va a empaquetar, sellar y mover de máquina, cada
dependencia de menos es una cosa menos que puede romperse.

**La tercera es que todos los demás importan de aquí.** El gateway, la API de telemetría, el módulo
de bloqueo, el perito, el compilador de informes y el servidor MCP leen la ruta de la bóveda y los
umbrales de `lab_env.py`. Los scripts que viven fuera de la carpeta `backend/`, como el perito o el
servidor MCP, añaden esa carpeta a su ruta de importación con una sola línea:

```python
sys.path.insert(0, str(ROOT_DIR / "backend"))
from lab_env import DB_PATH, ENTROPY_SQLI_THRESHOLD, CADENCE_THRESHOLD_MS, BURST_GAP_MS
```

Esa misma regla aparece dos veces más en el libro, aplicada a otras piezas. El bloqueo de firewall
vive en un solo módulo, `soar.py`, que comparten el gateway y el servidor MCP (capítulo 7). Y la
consulta que resume cada sesión vive en un solo módulo, `session_queries.py`, que comparten el panel
y el acta (capítulo 10). En los tres casos, el motivo es el mismo: el panel, el acta y el perito
tienen que decir lo mismo sobre la misma sesión, porque si no, ninguno de los tres es creíble.

## Lo que hay en la carpeta

Para terminar, el mapa del repositorio, con lo que vamos a tocar en cada capítulo:

```
vertex-forensic-lab/
├── backend/                  gateway, señuelos, SOAR y configuración (cap. 2-8, 10)
│   ├── lab_env.py            la única fuente de configuración
│   ├── main.py               middleware forense, señuelos y acciones
│   ├── swarm_canary.py       Canary Tokens (cap. 4)
│   ├── adaptive_tarpit.py    tarpit (cap. 5)
│   ├── soar.py               bloqueo en Windows Firewall (cap. 7)
│   ├── telemetry_api.py      API del HUD (cap. 8)
│   └── session_queries.py    resumen por sesión (cap. 10)
├── forensic_coroner_llm.py   perito híbrido (cap. 6)
├── forensic_report_compiler.py  acta con hash encadenado (cap. 10)
├── frontend/                 HUD en Angular 19
├── vertex-forensic-mcp/      servidor MCP y su cliente de prueba (cap. 11)
├── tmp/swarm_assault.sh      el ataque desde Parrot (cap. 9)
├── Start-VertexLab.ps1       arranque
├── Stop-VertexLab.ps1        parada y limpieza de reglas
└── logs/bitacora.md          la bitácora de la que salen todas las cifras del libro
```

## Lo que te llevas de aquí

- El laboratorio tiene cinco capas con responsabilidades separadas: el gateway mide y engaña, la
  bóveda guarda, el perito decide, el HUD muestra y el servidor MCP abre la evidencia a otros
  modelos.
- La superficie de mando (telemetría y acciones) es la parte más peligrosa del sistema, porque es la
  que controla las defensas.
- El perito es híbrido: Python decide con indicadores comprobables y el modelo local solo comenta.
- Un mismo dato copiado en varios sitios termina diciendo cosas distintas. El umbral de entropía
  valía 4.2 en un archivo y 4.5 en otros dos.
- `lab_env.py` es la única fuente de configuración. Las variables de entorno mandan, `.env` rellena
  lo que falta, y todos los demás módulos importan de ahí.
