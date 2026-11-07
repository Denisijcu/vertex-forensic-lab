# Capítulo 6 — El modelo asiste, no da fe

> Borrador. Fuente: forensic_coroner_llm.py, logs/bitacora.md (6 de noviembre de 2026, entradas de las
> 15:06, 15:13 y 15:22), reports/ACTA_FORENSE_VERTEX_20261106_152157.md y el acta final.

Con las medidas, la trampa y el tarpit, el laboratorio ya junta toda la evidencia que necesita. Falta
alguien que la lea y diga, para cada sesión: esto es un agente autónomo, o esto es un escáner
tradicional. Y que además lo explique en un texto que un humano pueda leer y que pueda ir en un acta.

Ese alguien es el **perito**. Este capítulo cuenta cómo se construyó, cómo falló tres veces durante
las pruebas y la decisión de diseño con la que terminó. Esa decisión le da título al capítulo y es,
probablemente, lo más útil que vas a sacar de este libro si trabajas con modelos de lenguaje en
cualquier sistema que tenga consecuencias.

## La tentación

La forma más rápida de construir un perito con un modelo de lenguaje es darle todos los datos de una
sesión y preguntarle: ¿qué es esto? Los modelos son buenos leyendo números y redactando
explicaciones. Un modelo local de pocos miles de millones de parámetros escribe dictámenes que
suenan expertos, en buen español técnico, en un segundo.

El problema es la palabra **suenan**. Un dictamen pericial no tiene que sonar bien. Tiene que ser
verdad, y tiene que poder demostrarse con la evidencia que lo acompaña. Un modelo de lenguaje
produce el texto más probable dados los datos, y el texto más probable no siempre coincide con el
correcto. Con números, en particular, los modelos pequeños se equivocan con una seguridad que da
miedo.

Por eso el perito de Vertex Forensic Lab separa desde el principio dos trabajos: **decidir** y
**redactar**.

## La parte que decide

La clasificación la hace Python, con indicadores que se pueden comprobar uno a uno contra la bóveda.
La función central devuelve dos listas, y la diferencia entre ellas es la clave de todo el diseño:

```python
def build_evidence(ua, cadence_ms, max_ent, tags, in_swarm, hit_canary):
    ind, notes = [], []
    if in_swarm:
        ind.append("participó en una transferencia lateral de Canary Token entre huellas distintas (swarm_lineage)")
    if "LATERAL_SWARM_HANDOFF" in tags:
        ind.append("presentó un Canary Token emitido a otra huella de sesión")
    if "TAMPERED_CANARY" in tags:
        ind.append("presentó un Canary Token con firma HMAC alterada")
    if max_ent >= ENTROPY_SQLI_THRESHOLD:
        ind.append(f"entropía máxima de {max_ent} bits, por encima del umbral de {ENTROPY_SQLI_THRESHOLD} bits")
    if cadence_ms >= CADENCE_THRESHOLD_MS:
        ind.append(f"cadencia mediana de {cadence_ms} ms dentro de ráfaga, ...")
    matched = [k for k in AGENT_UA_KEYWORDS if k in ua_upper]
    if matched:
        ind.append(f"el User-Agent declara un framework agéntico ({', '.join(matched)})")

    if hit_canary:
        notes.append("accedió al endpoint trampa /api/v1/system/config")
    if "SQLI_HIGH_ENTROPY" in tags:
        notes.append("envió cargas de inyección SQL")
    if "ADMIN_SURFACE_PROBE" in tags:
        notes.append("intentó acceder a la superficie de mando SOAR y fue rechazado con 403")
    return ind, notes
```

La primera lista son los **indicadores de agente**. Si hay al menos uno, la sesión es
`AUTONOMOUS_AI_AGENT`, con un 95 % de certeza. Si no hay ninguno, es `LEGACY_SCANNER`, con un 90 %.
La segunda lista son las **notas de contexto**: cosas que vale la pena dejar escritas en el dictamen,
pero que **no deciden** la clasificación.

¿Por qué separar? Por el segundo fallo de las pruebas.

## Fallo 1: la media (ya resuelto)

El primer fallo lo contó el capítulo 3: el Nikto salió como agente porque la cadencia se medía con la
media de todos sus Δt, y las pausas entre ejecuciones del script la inflaron a 46 381 ms. Con la
mediana dentro de ráfagas, la cadencia del Nikto es de 223.5 ms y ya no cruza el umbral.

## Fallo 2: la trampa que acusaba a cualquiera

En el mismo peritaje salió como agente otra sesión, `cd6aef3170f63c40`, con una sola petición y el
User-Agent `curl/8.14.1`. No había usado ningún token, su entropía era baja y su cadencia no se podía
medir. ¿Qué indicador la había acusado?

"Accedió al endpoint trampa." En la primera versión del perito, tocar la trampa contaba como
indicador de agente, con la lógica de que solo un explorador curioso pediría una ruta de
configuración. Esa sesión era la comprobación previa del propio script de ataque: un `curl` que
pedía la trampa solo para ver si el servidor respondía.

Y ahí estaba el error de razonamiento. Un escáner clásico **también** pide la trampa. Recorre todas
las rutas, una detrás de otra, y la trampa es una de ellas. El propio simulador del laboratorio hace
exactamente eso con su escáner de prueba. Tocar la trampa no distingue a un agente de un escáner. Lo
que los distingue es lo que viene después: **usar** el token desde otra huella. Y eso ya lo cubre el
primer indicador de la lista.

Lo mismo pasa con las otras dos notas de contexto. Un escáner envía inyecciones SQL, porque es lo que
hace un escáner. Y cualquier cliente puede pedir la superficie de mando. Son comportamientos hostiles
que merecen quedar escritos, pero no prueban que detrás haya un modelo razonando. De ahí la regla del
perito: **solo decide lo que separa a un agente de un escáner. Todo lo demás es contexto.**

La corrección tuvo una segunda parte, en el script de ataque: la comprobación previa dejó de pedir la
trampa y ahora pide la raíz `/`, con su propia huella (`Vertex-Precheck/1.3`), para no contaminar la
evidencia con tráfico del propio banco de pruebas.

## Fallo 3: el modelo que no estaba listo

En ese mismo primer peritaje, el modelo local devolvió un error HTTP 400 en las dos primeras
sesiones y respondió bien en las siguientes. El perito, que entonces no reintentaba, pasó esas dos
sesiones al dictamen de respaldo.

El patrón, primeras peticiones fallidas y el resto correctas, apuntaba a que el modelo todavía se
estaba cargando en memoria cuando llegaron. LM Studio puede cargar los modelos bajo demanda, y la
primera petición encuentra el modelo a medio subir. La corrección fue reintentar hasta tres veces,
esperando más en cada intento, e imprimir el cuerpo del error en el registro para que, si vuelve a
pasar, se vea la causa real en lugar de suponerla:

```python
for attempt in range(1, LLM_RETRIES + 1):
    resp = client.post(LM_STUDIO_URL, json=payload)
    if resp.status_code == 200:
        return resp.json()["choices"][0]["message"]["content"]
    detail = resp.text.strip().replace("\n", " ")[:220]
    print(f"    [!] LM Studio HTTP {resp.status_code} en {fp[:8]} (intento {attempt}/{LLM_RETRIES}): {detail}")
    if attempt < LLM_RETRIES:
        time.sleep(2.0 * attempt)
```

En el siguiente peritaje, con las tres correcciones, las cuatro sesiones nuevas se resolvieron sin un
solo error, y con la clasificación correcta: el Scout y el Exploit como agentes, el Nikto y la
comprobación previa como escáneres.

## La parte que redacta

Con la clasificación decidida, el perito le pide al modelo local que redacte el dictamen. El prompt
no le pregunta qué es la sesión. Le **dice** qué es, y le da los indicadores ya confirmados:

```
Redacta en español técnico, en UNA sola oración, el dictamen de esta sesión.
Clasificación ya confirmada por telemetría: LEGACY_SCANNER.
Indicadores de agente confirmados (úsalos tal cual, no inventes otros):
  - ninguno
Contexto adicional:
  - ninguno
Datos: 12 peticiones, cadencia mediana 223.5 ms, entropía máxima 3.992 bits (umbral 4.5 bits), ...
No califiques como 'alta' una entropía por debajo del umbral.
```

Y la respuesta se pide con un esquema JSON estricto que solo tiene un campo, `reasoning`. El modelo
no puede devolver una clasificación ni una certeza, porque el esquema no tiene sitio para ellas. Con
eso pensé que estaba resuelto.

No lo estaba.

## Siete de nueve

La primera acta exportada con tráfico real desde Parrot tenía los datos perfectos: nueve sesiones,
cada una con su veredicto correcto, 15 transferencias de token y el bloqueo propagado a las cinco
sesiones de Parrot. Pero cuando leí los dictámenes, uno por uno, **siete de los nueve contradecían la
evidencia que los acompañaba**.

Del Scout, con una entropía máxima de 3.914 bits, el modelo escribió que esa entropía "supera el
umbral establecido para considerarlo 'alta'". El umbral era 4.5. Del Nikto escribió que tenía "el
alto valor de entropía (3.992 bits) que supera el umbral recomendado (4.5 bits)". El número y el
umbral estaban en la misma frase, y la frase los comparaba al revés.

De la comprobación previa, un escáner sin ningún indicador, escribió que "podría ser un agente
malicioso". Del Nikto de las pruebas antiguas, que su actividad estaba "potencialmente asociada con
malware". Ninguna de las dos afirmaciones tenía base en la evidencia, y las dos contradecían el
veredicto que la propia línea de encima declaraba.

Y en dos dictámenes, el modelo repitió la instrucción del prompt como si fuera una conclusión: "No
calificamos como 'alta' la entropía por debajo del umbral". La frase que le había dado para evitar un
error terminó pegada en el acta.

Yo tenía un validador. Rechazaba los textos en inglés y los que contenían la frase "alta entrop"
junto a una cifra por debajo del umbral. Ninguno de los siete la contenía. El modelo decía lo mismo
con otras palabras: "alto valor de entropía", "entropía máxima alta", "que supera el umbral". Un
validador que busca una frase concreta contra un generador de frases nuevas pierde siempre.

## La decisión

Había dos caminos. El primero era seguir afinando el validador: más patrones, más casos, más
excepciones. Lo hice, y el validador quedó mucho mejor. Revisa el texto frase a frase, extrae todas
las cifras en bits de cada frase y rechaza la frase si una cifra por debajo del umbral aparece junto a
palabras como "supera", "superior", "por encima", "alta" o "elevada" sin un "inferior" o "por debajo"
que la corrija. Rechaza también el eco del prompt, y prohíbe que el dictamen de un escáner hable de
agentes, malware, ataques o actividad anómala.

Pero un validador más listo sigue siendo un validador. Algún día el modelo escribirá un error con
palabras que el validador no prevé, y ese día el error llegará al acta con un sello SHA-256 encima.

Así que tomé el segundo camino, que cambia el papel del modelo en el sistema:

> **El dictamen oficial del acta es siempre el determinista. El texto del modelo es un comentario no
> vinculante, y solo se guarda si pasa el validador.**

El dictamen determinista no lo escribe ningún modelo. Lo construye Python a partir de los mismos
indicadores que decidieron la clasificación:

```python
def deterministic_reasoning(expected_class, indicators, notes, cadence_ms, max_ent):
    extra = f" Contexto: {'; '.join(notes)}." if notes else ""
    if expected_class == "AUTONOMOUS_AI_AGENT":
        return "Clasificada como agente autónomo porque " + "; ".join(indicators) + "." + extra
    cadencia = (f"su cadencia mediana ({cadence_ms} ms) es mecánica" if cadence_ms > 0
                else "no presenta ráfagas de peticiones consecutivas")
    return (f"Clasificada como escáner tradicional: no participó en transferencias de Canary Token, no declara "
            f"un framework agéntico, su entropía máxima ({max_ent} bits) queda por debajo de "
            f"{ENTROPY_SQLI_THRESHOLD} bits y {cadencia}.{extra}")
```

Es menos elegante que un párrafo redactado por un modelo. A cambio, **cada palabra se puede
verificar**. Así quedó el dictamen del Nikto en el acta final:

> Clasificada como escáner tradicional: no participó en transferencias de Canary Token, no declara un
> framework agéntico, su entropía máxima (3.992 bits) queda por debajo de 4.5 bits y su cadencia
> mediana (223.5 ms) es mecánica.

Y así el del Exploit:

> Clasificada como agente autónomo porque participó en una transferencia lateral de Canary Token entre
> huellas distintas (swarm_lineage); presentó un Canary Token emitido a otra huella de sesión; entropía
> máxima de 5.716 bits, por encima del umbral de 4.5 bits; cadencia mediana de 7791.45 ms dentro de
> ráfaga, compatible con pausas de inferencia (umbral 1000 ms); el User-Agent declara un framework
> agéntico (LANGGRAPH, AUTOGPT, SWARM). Contexto: envió cargas de inyección SQL; intentó acceder a la
> superficie de mando SOAR y fue rechazado con 403.

Cada cláusula de ese párrafo corresponde a una fila de la bóveda. Un abogado, un auditor o un
compañero escéptico puede tomar cualquiera de ellas y comprobarla con una consulta SQL.

El modelo sigue en el sistema. Sus comentarios se guardan en el campo `llm_commentary` del veredicto,
y el registro del perito dice en cada sesión si el comentario pasó el validador o por qué se
descartó. Puede ser útil para un operador que quiere una segunda lectura en lenguaje natural. Pero no
entra en el documento que se firma.

## La idea que se queda

Si trabajas con modelos de lenguaje en cualquier sistema que tenga consecuencias, esta es la idea que
quiero que te lleves de este capítulo: hay una diferencia entre **asistir** y **dar fe**.

Un modelo puede asistir muy bien. Puede resumir, sugerir, redactar un borrador, encontrar un patrón
que se te escapó. Pero dar fe es afirmar, con tu firma debajo, que algo es verdad. Eso exige que cada
afirmación se pueda rastrear hasta una evidencia, y un texto generado no se puede rastrear: suena
igual de seguro cuando acierta que cuando se equivoca.

En un acta forense, en un informe financiero, en un diagnóstico, en cualquier documento que alguien
va a usar para tomar una decisión, el modelo puede ser el asistente del perito. No puede ser el
perito.

## Lo que te llevas de aquí

- El perito separa decidir de redactar. Python decide con indicadores comprobables; el modelo, en el
  mejor de los casos, comenta.
- Solo decide lo que separa a un agente de un escáner: transferencia de token, token alterado,
  entropía alta, cadencia de inferencia y User-Agent agéntico. Tocar la trampa, inyectar SQL o pedir
  la superficie de mando son contexto, porque un escáner también lo hace.
- Un error 400 solo en las primeras peticiones suele ser el modelo cargándose: reintenta con espera e
  imprime el cuerpo del error.
- Con tráfico real, 7 de 9 dictámenes del modelo contradecían la evidencia, aunque el modelo ya
  recibía la clasificación y los indicadores hechos.
- Un validador que busca frases concretas pierde contra un generador de frases nuevas.
- El dictamen oficial es determinista y verificable cláusula a cláusula. El modelo asiste, pero no da
  fe.
