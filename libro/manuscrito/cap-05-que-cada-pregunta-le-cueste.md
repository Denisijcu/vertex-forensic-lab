# Capítulo 5 — Que cada pregunta le cueste

> Borrador. Fuente: backend/adaptive_tarpit.py, backend/main.py (pesos de anomalía),
> logs/bitacora.md (6 de noviembre de 2026, entradas de las 15:00 y 15:03) y la tabla de linaje del acta final.

Detectar a un atacante no lo detiene. Entre el momento en que el laboratorio sospecha de una sesión
y el momento en que el operador pulsa el botón de aislar, el atacante sigue trabajando. Puede pasar
un minuto, o una hora si es de noche y nadie mira el panel.

Este capítulo construye la defensa que actúa en ese intervalo, sin esperar a nadie: el **tarpit**.
La palabra viene de los pozos de brea donde quedaban atrapados los animales prehistóricos. Cuanto
más se movían, más se hundían. Aquí la idea es la misma: cuanto más sospechoso se comporta un
cliente, más tarda el servidor en responderle.

## Por qué el tiempo duele más a un agente

Un retraso de unos segundos apenas molesta a un escáner tradicional. Lanza miles de peticiones en
paralelo, y unas cuantas lentas no cambian su resultado. Pero un agente de IA trabaja de otra forma.
Lee cada respuesta antes de decidir la siguiente petición, así que sus pasos son secuenciales: no
puede lanzar el paso cuatro sin haber leído el paso tres.

Además, los orquestadores de agentes suelen trabajar con presupuestos. Un número máximo de pasos,
un tiempo máximo por tarea, un límite de tokens. Cada segundo que el servidor retiene una respuesta
es un segundo que el agente pasa esperando, con su ventana de trabajo abierta. Si las respuestas se
vuelven lo bastante lentas, el orquestador da la tarea por fallida o el agente agota su presupuesto
antes de llegar a ningún sitio.

El tarpit no bloquea nada. Simplemente hace que atacar sea caro.

## El puntaje de sospecha

El motor del tarpit es pequeño. Lleva un puntaje por huella de sesión, y cada comportamiento
sospechoso le suma un peso:

```python
class AdaptiveTarpitEngine:
    def __init__(self):
        self.suspicion_scores: dict[str, int] = defaultdict(int)

    def register_anomaly(self, session_fp: str, weight: int = 1) -> int:
        self.suspicion_scores[session_fp] += weight
        return self.suspicion_scores[session_fp]
```

Los pesos los pone el middleware según lo que detecta en cada petición:

| Comportamiento | Peso |
|---|---|
| Presentar un Canary Token válido | 3 |
| Presentar un Canary Token falsificado | 3 |
| Carga con entropía alta, comilla simple o `UNION` | 2 |
| Pedir la superficie de mando desde la red | 2 |

Los tokens pesan más que las cargas porque son una prueba más fuerte. Una comilla en una consulta
puede ser un error tipográfico. Un token emitido a otra huella no puede ser casualidad.

## La curva del retraso

Con el puntaje acumulado, el motor calcula cuánto retener la respuesta:

```python
def get_delay_seconds(self, session_fp: str) -> float:
    score = self.suspicion_scores.get(session_fp, 0)
    if score <= 1:
        return 0.0
    return min(0.35 * (1.75 ** (score - 1)), 6.0)
```

Tres decisiones caben en esas cuatro líneas.

**Por debajo de 2 puntos no hay retraso.** Un único comportamiento leve no debe castigar a un
cliente legítimo. El tarpit empieza cuando la sospecha se acumula.

**La curva es exponencial.** Cada punto extra multiplica el retraso por 1,75. Así, una sesión
ligeramente sospechosa apenas lo nota, y una que insiste se hunde deprisa:

| Puntaje | Retraso |
|---|---|
| 2 | 0.61 s |
| 3 | 1.07 s |
| 4 | 1.88 s |
| 5 | 3.28 s |
| 6 | 5.74 s |
| 7 o más | 6.00 s (tope) |

**Hay un tope de 6 segundos.** Un retraso infinito sería, en la práctica, un bloqueo, y además
dejaría conexiones abiertas en el servidor indefinidamente. Seis segundos es lo bastante largo para
arruinar el ritmo de un agente y lo bastante corto para que el laboratorio no acumule sockets
colgados.

La retención en sí es una espera asíncrona:

```python
async def apply_tarpit_if_needed(self, session_fp: str) -> float:
    delay_sec = self.get_delay_seconds(session_fp)
    if delay_sec > 0:
        await asyncio.sleep(delay_sec)
    return round(delay_sec * 1000.0, 2)
```

Que sea `await asyncio.sleep` y no `time.sleep` es importante. La espera asíncrona libera el
servidor para atender otras peticiones mientras tanto. El atacante espera, pero el resto del tráfico
no lo nota.

## Lo que se midió

El Exploit de Parrot, en su primer impacto, presentaba un token robado (3 puntos) con una inyección
SQL (2 puntos): 5 puntos de golpe, 3.28 segundos de retraso. En el segundo impacto ya acumulaba 10
puntos, muy por encima del tope.

No tengo el tiempo de respuesta de cada impacto de esa primera ejecución impreso en una consola. Pero
lo puedo reconstruir sin estimar nada, a partir de los tiempos de tránsito del linaje, que sí están
medidos. Cada tránsito es el tiempo desde que el Scout recibió el token hasta que llegó un impacto
del Exploit. Entre un impacto y el siguiente, el script esperaba 1.4 segundos después de recibir la
respuesta. Así que la diferencia entre dos tránsitos consecutivos, menos esos 1.4 segundos, es lo
que tardó en volver la respuesta del impacto anterior:

| Ejecución | Tránsitos medidos | Respuesta del impacto 1 | Respuesta del impacto 2 |
|---|---|---|---|
| Primera | 1825 · 6905 · 14688 ms | 6905 − 1825 − 1400 = **3680 ms** | 14688 − 6905 − 1400 = **6383 ms** |
| Segunda | 1824 · 9664 · 17487 ms | 9664 − 1824 − 1400 = **6440 ms** | 17487 − 9664 − 1400 = **6423 ms** |

En la primera ejecución, el primer impacto tardó unos 3.7 segundos: los 3.28 del tarpit más el costo
propio de la petición, del que hablo enseguida. A partir de ahí, todos los impactos rondan los 6.4
segundos: el tope de 6 más ese mismo costo.

Las ejecuciones con la versión final del script, en las que la consola de Parrot sí imprimía cada
tiempo, lo confirman: **6.388, 6.377 y 6.390 segundos** en una, y **6.443, 6.355 y 6.375** en otra.
Mientras tanto, los tres sondeos del escáner Nikto, que no sumaban ningún peso, volvían en **0.19 a
0.22 segundos**.

Treinta veces más lento para el que ataca. Ningún retraso para el que solo mira.

## Hallazgo 1: el puntaje que nunca baja

La segunda ejecución trajo una sorpresa: su primer impacto ya tardó 6.4 segundos, no 3.7. El
atacante empezaba directamente en el tope.

La razón está en el diseño del motor. El puntaje vive en un diccionario en memoria, indexado por
huella, y **solo sabe sumar**. Mientras el gateway sigue en marcha, el puntaje de una huella nunca
baja. Y la huella del Exploit (misma IP, mismo User-Agent, mismo nodo) era idéntica de una ejecución
a otra. El Exploit de la segunda ejecución heredó los puntos que había acumulado el de la primera.

¿Es un error? Depende de cómo lo mires. Para un laboratorio de pruebas es un inconveniente, porque
no puedes repetir un experimento en las mismas condiciones sin reiniciar el gateway. Para la defensa
real, castigar a un atacante reincidente con el retraso máximo desde el primer paso no está mal. Lo
que no está bien es que el puntaje no tenga ningún **decaimiento**: un cliente que hizo una petición
sospechosa hace una semana no debería seguir penalizado hoy. Y en un servidor que corre durante
meses, un diccionario que solo crece es memoria que nunca se libera.

La corrección queda anotada para la siguiente versión: que el puntaje decaiga con el tiempo, por
ejemplo a la mitad cada cierto número de minutos sin actividad, y que las huellas inactivas se
borren del diccionario.

## Hallazgo 2: el costo de cada petición

Si el tope del tarpit es de 6 segundos, ¿por qué los impactos tardaban 6.4? ¿Y por qué el Nikto, sin
ningún retraso, tardaba 0.2 segundos en recibir un simple error?

Esos 0.2 segundos son el costo propio de cada petición, y casi todo sale de la bóveda. El middleware
**abre y cierra una conexión a DuckDB en cada petición** para guardar la evidencia. En Windows, abrir
el archivo de la base de datos no es gratis. Y las peticiones del Exploit pagan ese costo dos veces:
una para escribir la fila del linaje y otra para la evidencia. De ahí los aproximadamente 0.4
segundos de más sobre el tope.

Para un laboratorio es tolerable. Para un gateway que tenga que atender tráfico real, no: 0.2
segundos por petición es una eternidad. La mejora también está anotada para la siguiente versión:
una sola conexión por proceso, que se abre al arrancar y se reutiliza en cada petición.

Lo cuento aquí, y no en el capítulo de lo que falla, por una razón: es la clase de cosa que solo
descubres cuando mides. En el código, abrir una conexión por petición parece limpio y seguro. En la
consola de Parrot, se ve como un suelo de 0.2 segundos que no baja nunca.

## Lo que te llevas de aquí

- El tarpit actúa mientras nadie mira: no bloquea, retrasa las respuestas a las sesiones
  sospechosas para que atacar sea caro.
- Duele más a un agente que a un escáner, porque el agente trabaja paso a paso y con presupuesto.
- Cada huella acumula un puntaje (3 por token, 2 por inyección o por tocar la superficie de mando).
  El retraso crece de forma exponencial y tiene un tope de 6 segundos.
- La espera es asíncrona: el atacante espera, el resto del servidor no.
- Medido desde Parrot: el Exploit, unos 6.4 segundos por impacto; el Nikto, unos 0.2.
- El puntaje nunca baja mientras el gateway corre, y abrir DuckDB en cada petición cuesta unos 0.2
  segundos. Ambas cosas solo se vieron al medir, y quedan para la siguiente versión.
