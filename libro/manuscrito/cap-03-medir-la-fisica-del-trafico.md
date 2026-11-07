# Capítulo 3 — Medir la física del tráfico

> Borrador. Fuente: backend/main.py (middleware forense), backend/session_queries.py,
> forensic_coroner_llm.py, logs/bitacora.md (6 de noviembre de 2026, entradas de las 15:06 y 15:25)
> y el acta final.

Un cortafuegos de firmas pregunta "¿esta petición se parece a un ataque que ya conozco?". Es una
buena pregunta para un escáner, que repite siempre las mismas cargas. Es una mala pregunta para un
agente, que escribe cada carga nueva a partir de lo que leyó en la respuesta anterior.

Vertex Forensic Lab hace otra pregunta: **¿cómo se comporta este cliente?** No mira qué dice cada
petición, sino cómo llegan: quién las envía, cuánto desorden llevan dentro y cuánto tiempo pasa
entre una y otra. Son tres medidas físicas, en el sentido de que no dependen de conocer el ataque de
antemano. Este capítulo las construye, y termina con la historia del error de medida más instructivo
de todo el proyecto.

## Medida 1: la huella de sesión

Para hablar de "el comportamiento de un cliente" primero hay que poder decir qué peticiones son del
mismo cliente. La forma habitual es una cookie de sesión, pero un atacante controla sus cookies: las
borra, las cambia o no las envía. Necesitamos una identidad que no dependa de la buena voluntad del
cliente.

La huella del laboratorio se calcula sin estado, a partir de tres datos que vienen en cada petición:

```python
def compute_session_fingerprint(ip: str, user_agent: str, swarm_node: str) -> str:
    raw = f"{ip}|{user_agent}|{swarm_node}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
```

La IP de origen, el User-Agent y la cabecera `X-Swarm-Node`, unidos con una barra vertical y pasados
por SHA-256. Los primeros 16 caracteres hexadecimales, 64 bits, son la huella. El resultado tiene
una propiedad útil para un laboratorio de enjambres: **dos papeles del mismo atacante tienen huellas
distintas aunque salgan de la misma IP.** En las pruebas, el Scout y el Exploit salieron de
`172.28.56.172`, pero con User-Agents distintos (`CrewAI-Recon-Scout/3.1` y
`AutoGPT-Swarm-Exploit/4.0`), y el laboratorio los registró como `520cc6f8db327e75` y
`a9101753d8dd5018`. Esa separación es la que permite ver, en el capítulo 4, que uno le pasa algo
al otro.

Una advertencia honesta: esta huella identifica una combinación, no a una persona. Un atacante que
cambie de User-Agent en cada petición genera una huella nueva en cada petición. El laboratorio no
intenta resolver eso con la huella. Lo resuelve de otras formas: la trampa del capítulo 4 enlaza
huellas distintas mediante el token que comparten, y la contención del capítulo 7 bloquea por IP, no
por huella.

## Medida 2: la entropía de Shannon

La segunda medida responde a "¿cuánto desorden lleva esta petición?". La herramienta es la
**entropía de Shannon**: el número medio de bits que hace falta para codificar cada carácter de un
texto, dada la frecuencia con que aparece cada uno.

$$H(X) = -\sum_{i} P(x_i) \log_2 P(x_i)$$

En la práctica, eso se traduce en unas pocas líneas:

```python
def calculate_shannon_entropy(data: str) -> float:
    if not data:
        return 0.0
    length = len(data)
    counts = Counter(data)
    return -sum((count / length) * math.log2(count / length) for count in counts.values())
```

El laboratorio la calcula sobre la ruta, los parámetros de consulta y la cabecera de autorización,
todo junto:

```python
raw_inspection_str = f"{path}?{request.url.query} {auth_hdr}".strip()
entropy = calculate_shannon_entropy(raw_inspection_str)
```

¿Por qué funciona? Porque el tráfico normal es repetitivo. Una ruta como
`/api/v2/internal/vault?node_id=1` tiene pocos caracteres distintos y muchos repetidos: barras,
letras minúsculas, algún número. Las cargas de un ataque, en cambio, mezclan comillas, paréntesis,
signos de igual, palabras clave en mayúsculas, comentarios con caracteres aleatorios y, si trae un
token, una cadena larga en base64. Cuantos más símbolos distintos y más repartidos, más entropía.

Las cifras medidas en las pruebas lo muestran con claridad:

| Petición | Entropía máxima |
|---|---|
| Comprobación previa a `/` | 1.0 bits |
| Scout pidiendo la configuración | 3.914 bits |
| Nikto sondeando la bóveda | 3.992 bits |
| Exploit con token e inyección SQL | 5.716 bits |

El laboratorio usa un umbral de **4.5 bits**. Por encima, la petición recibe la etiqueta
`SQLI_HIGH_ENTROPY` y suma peso de sospecha. La etiqueta también se pone, aunque la entropía no
llegue al umbral, si la consulta trae una comilla simple (literal o codificada como `%27`) o la
palabra `UNION`:

```python
query_upper = request.url.query.upper()
if entropy >= ENTROPY_SQLI_THRESHOLD or "'" in request.url.query or "%27" in query_upper or "UNION" in query_upper:
    deception_tag = f"{deception_tag}|SQLI_HIGH_ENTROPY"
    tarpit_engine.register_anomaly(fp, weight=2)
```

Fíjate en que la entropía por sí sola no basta para acusar a nadie. Una ruta legítima con un token
largo puede superar el umbral sin ser un ataque. Por eso la entropía es un indicador entre varios, y
el perito nunca clasifica a una sesión como agente solo por ella sin dejar constancia de cuál fue la
cifra exacta.

## Medida 3: la cadencia

La tercera medida es la más interesante, porque es la que distingue mejor a una máquina que repite
de una máquina que piensa. Responde a "¿cuánto tiempo pasa entre una petición y la siguiente de este
mismo cliente?".

El middleware guarda en memoria la última vez que vio cada huella, y calcula la diferencia:

```python
prev_ts = LAST_SEEN_TS.get(fp)
delta_t_ms = (now - prev_ts) * 1000.0 if prev_ts is not None else 0.0
LAST_SEEN_TS[fp] = now
```

Ese Δt se guarda con cada evidencia. La idea es simple: un escáner dispara la siguiente petición en
cuanto recibe la anterior, así que sus Δt son cortos y regulares, del orden de lo que tarda la red.
Un agente de IA lee la respuesta, la pasa por un modelo de lenguaje, razona y escribe la siguiente
carga. Eso lleva segundos. Sus Δt son largos.

El laboratorio considera "cadencia de inferencia" cualquier valor de **1000 ms o más**. Hasta aquí,
todo parece sencillo. El problema está en cómo se resume la cadencia de una sesión entera en un solo
número.

## El caso del Nikto que parecía un agente

En la primera ronda de peritaje con tráfico real desde Parrot, el perito clasificó al escáner Nikto,
la sesión `d7820db79437fa84`, como **agente autónomo**.

No tenía ningún indicador de agente. No había tocado ningún token, su entropía máxima era de 3.992
bits y su User-Agent decía claramente `Nikto/2.1.6`. Pero el perito le atribuyó una cadencia media de
**46 381 ms**, muy por encima del umbral de 1000, y con eso bastó para acusarlo.

¿De dónde salían 46 segundos entre peticiones de un escáner que dispara en ráfaga? De la forma en
que se hicieron las pruebas. El script de ataque se lanzó varias veces a lo largo de la tarde, y en
cada ejecución el Nikto hacía tres peticiones seguidas. Entre una ejecución y la siguiente pasaban
varios minutos: el tiempo de revisar el panel, corregir algo y volver a lanzar. Como la huella era
la misma en todas las ejecuciones (misma IP, mismo User-Agent, mismo nodo), el laboratorio veía una
sola sesión con nueve peticiones, y algunos de sus Δt eran de minutos.

Esta es la forma de los Δt de esa sesión. Los valores dentro de cada ráfaga rondan los 200 ms, como
confirmó después la mediana; las pausas entre ráfagas duran lo que tardó el operador en volver a
lanzar el script:

```
ráfaga 1:  0 ms                 ~200 ms   ~200 ms
ráfaga 2:  [pausa de minutos]   ~200 ms   ~200 ms
ráfaga 3:  [pausa de minutos]   ~200 ms   ~200 ms
```

La media de esos valores sale enorme, porque dos o tres pausas largas pesan más que todas las
peticiones cortas juntas. **La media mezcla dos cosas que no tienen nada que ver**: el ritmo del
cliente dentro de una ráfaga, que es lo que queremos medir, y el tiempo que el operador tardó en
volver a lanzar el script, que no dice nada del cliente.

La corrección tiene dos partes, y las dos son necesarias.

**La primera es cambiar la media por la mediana.** La mediana es el valor del medio cuando ordenas
todos los Δt. Si la mayoría de las peticiones llegan a 200 ms, la mediana es unos 200 ms, por
grandes que sean las pausas aisladas. Es mucho más resistente a los valores extremos.

**La segunda es descartar las pausas entre ráfagas.** La mediana sola mejora mucho, pero si una
sesión tiene pocas peticiones, unas cuantas pausas largas todavía pueden moverla. Así que el
laboratorio solo cuenta los Δt mayores que cero (la primera petición de una sesión no tiene
anterior) y menores o iguales que 30 segundos. Un Δt de más de 30 segundos no es cadencia de
inferencia: es que el cliente se fue y volvió.

En SQL de DuckDB, las dos cosas caben en una sola expresión:

```sql
ROUND(COALESCE(MEDIAN(e.delta_t_ms)
      FILTER (WHERE e.delta_t_ms > 0 AND e.delta_t_ms <= 30000), 0), 2) AS cadence_ms
```

Con esa medida, la misma sesión del Nikto da una cadencia de **223.5 ms**. Mecánica pura. Y el
Exploit, que entre impacto e impacto esperaba 1.4 segundos y además sufría el tarpit, da **7791.45
ms**. Ahora los dos números cuentan la verdad sobre cada cliente.

## Cuando la cadencia es cero

La corrección deja un caso que conviene entender, porque aparece varias veces en el acta: sesiones
con **cadencia mediana de 0.0 ms**. Son el Scout, la comprobación previa del script y el `curl`
simple. No es que respondan instantáneamente. Es que **no tienen ningún Δt dentro de una ráfaga**:
el Scout hace una sola petición por ejecución, así que todos sus Δt son o cero (la primera) o pausas
de minutos entre ejecuciones, que se descartan.

Por eso el perito trata el cero como "no hay ráfagas", no como "cadencia mecánica". El dictamen de
la comprobación previa lo dice así: *"no presenta ráfagas de peticiones consecutivas"*. Una medida
que no se puede tomar se declara como tal. No se convierte en una afirmación.

## Una sola fórmula para todos

Hubo un último detalle, y es la regla del capítulo 2 en acción. Después de corregir el perito, el
panel seguía mostrando el **Δt medio**, porque su consulta era distinta. La tarjeta del Exploit
decía "Media Delta T: 54 860 ms" mientras el perito razonaba con 7791 ms. Dos números para la misma
sesión, en la misma pantalla.

La solución fue sacar la consulta a un módulo propio, `backend/session_queries.py`, que usan a la vez
el panel y el acta. Y los dos umbrales, el de 1000 ms y el de 30 segundos, pasaron a vivir en
`lab_env.py`, de donde los lee también el perito. Desde entonces, la tarjeta, el dictamen y el acta
dicen la misma cifra, porque salen de la misma fórmula.

## Lo que te llevas de aquí

- El laboratorio mide cómo se comporta un cliente, no qué dice cada petición: huella, entropía y
  cadencia.
- La huella es el SHA-256 de IP, User-Agent y nodo, sin cookies. Separa los papeles de un mismo
  atacante aunque compartan IP.
- La entropía de Shannon sube con el desorden: 3.9 bits para una ruta normal, 5.7 para una carga con
  token e inyección. El umbral es 4.5 bits.
- La media de los Δt mezcla el ritmo del cliente con las pausas del operador. Hizo que un Nikto
  pareciera un agente (46 381 ms).
- La cadencia correcta es la mediana de los Δt dentro de ráfagas, entre 0 y 30 segundos: 223.5 ms
  para el Nikto y 7791 ms para el Exploit.
- Una medida que no se puede tomar se declara como tal. Cadencia cero significa "sin ráfagas", no
  "mecánico".
