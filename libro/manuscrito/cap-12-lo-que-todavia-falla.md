# Capítulo 12 — Lo que todavía falla

> Borrador. Fuente: logs/bitacora.md (6 de noviembre de 2026, sección "Pendientes para una v1.4" y entradas
> de las 15:00, 15:25), el acta final y los capítulos 5, 10 y 11.

Como en los libros anteriores de esta serie, el último capítulo técnico no trata de lo que funciona,
sino de lo que no. Vertex Forensic Lab pasó la prueba de fuego: detectó el enjambre, lo frenó, lo
peritó, lo dejó fuera y firmó un acta coherente. Pero durante las pruebas y mientras escribía este
libro aparecieron problemas que siguen ahí. Algunos son menores. Otros no.

Los cuento todos, con su causa y con lo que haría para corregirlos. Si vas a usar este laboratorio, o
a construir algo parecido, necesitas saber dónde no fiarte de él.

## 1. El puntaje del tarpit no olvida

**Lo que pasa.** El puntaje de sospecha de cada huella solo sabe sumar, y vive en memoria mientras el
gateway está en marcha. En la segunda ronda de pruebas, el Exploit empezó directamente en el tope de 6
segundos porque heredó los puntos de la primera.

**Por qué importa.** En un servidor que corre durante meses, un cliente que hizo algo sospechoso una vez
seguiría penalizado para siempre, y el diccionario de puntajes crecería sin límite con cada huella nueva.
Además, el puntaje se pierde por completo al reiniciar el gateway, que es justo lo contrario de lo que
querrías con un atacante persistente.

**Cómo lo corregiría.** Con un decaimiento por tiempo: el puntaje se reduce a la mitad tras cierto
intervalo sin actividad, y las huellas que llegan a cero se borran. Y, opcionalmente, guardando los
puntajes en la bóveda para que sobrevivan a un reinicio.

## 2. Una conexión a DuckDB por petición

**Lo que pasa.** El middleware abre y cierra una conexión a la bóveda en cada petición. En las pruebas,
eso puso un suelo de unos 0.2 segundos a cada respuesta, incluso a las que no tenían ningún retraso del
tarpit, y añadió unos 0.4 segundos a las del Exploit, que escribían dos veces.

**Por qué importa.** Para un laboratorio es aceptable. Para un gateway delante de una API real, 0.2
segundos por petición es inasumible. Y hay un segundo problema: DuckDB solo admite un proceso escribiendo
a la vez. El perito y el servidor MCP abren la misma bóveda desde otros procesos, y si coinciden con una
escritura del gateway, uno de ellos puede recibir un error de bloqueo del archivo. Durante las pruebas no
llegó a pasar porque el perito se lanzó siempre con el ataque ya terminado, pero con tráfico continuo no
habría esa pausa.

**Cómo lo corregiría.** Una sola conexión por proceso en el gateway, abierta al arrancar. Y, para los
demás procesos, que no abran el archivo directamente, sino que pidan los datos al gateway, que es el
único que escribe.

## 3. El Scout no deja su marca

**Lo que pasa.** Cuando el Scout pide la trampa y recibe el token, esa petición se registra con la
etiqueta genérica `STANDARD_PROBE`. En el acta final, la sesión del Scout aparece con esa etiqueta, aunque
fue la que robó el token.

**Por qué importa.** La información no se pierde: el perito sabe que el Scout tocó la trampa y que
participó en el linaje. Pero quien lea la columna de etiquetas del acta no ve que esa sesión fue el
origen del enjambre.

**Cómo lo corregiría.** Etiquetando como `CANARY_MINTED` la petición en la que se emite un token.

## 4. Dos indicadores que dicen casi lo mismo

**Lo que pasa.** En los dictámenes de los Exploit, los dos primeros indicadores son "participó en una
transferencia lateral de Canary Token entre huellas distintas" y "presentó un Canary Token emitido a otra
huella de sesión". El primero se deduce del linaje y el segundo de la etiqueta de la petición, pero
describen el mismo hecho.

**Por qué importa.** No cambia ninguna clasificación, pero un lector puede pensar que son dos pruebas
independientes cuando son una sola. En un documento pericial, contar dos veces la misma prueba es un
defecto, aunque sea de forma.

**Cómo lo corregiría.** Fusionándolos en un solo indicador, y dejando el detalle del linaje en el contexto.

## 5. El acta prueba integridad, no autoría

**Lo que pasa.** El capítulo 10 lo explicó: el SHA-256 del acta demuestra que no ha cambiado, pero no
quién la emitió ni cuándo. Cualquiera con acceso a la carpeta podría modificar el acta y recalcular sus
hashes.

**Cómo lo corregiría.** Firmando el acta con una clave privada del laboratorio, añadiendo un sello de
tiempo de un tercero, o al menos enviando el hash fuera de la máquina en el momento de exportarla.

## 6. El asistente lee lo que escribe el atacante

**Lo que pasa.** El capítulo 11 lo contó: las herramientas MCP devuelven al modelo evidencias que en
parte escribió el atacante, como la ruta de cada petición. Un atacante puede esconder en ellas
instrucciones dirigidas al modelo.

**Por qué importa.** Es el riesgo más serio de esta lista, porque combina un modelo que lee contenido
hostil con una herramienta que puede bloquear IPs.

**Cómo lo corregiría.** Marcando en la salida de las herramientas qué campos vienen del cliente remoto,
recortando su longitud y neutralizando los textos que parezcan instrucciones. Hasta entonces, la regla
es la del capítulo 11: la herramienta de bloqueo, siempre con confirmación humana.

## 7. Docker, sin probar

**Lo que pasa.** El `docker-compose.yml` quedó corregido en la revisión: la ruta de la bóveda, la subred
que chocaba con WSL, el secreto fuera del archivo y la variable que leía el simulador. Pero **no lo he
probado**. Todas las pruebas del libro se hicieron con el laboratorio corriendo directamente en Windows.

Hay además una incógnita concreta. Dentro del contenedor, el panel del anfitrión no llega por loopback,
sino a través de la red puente de Docker. El compose permite esa red con
`VERTEX_ADMIN_ALLOWED_CIDRS=10.88.0.1/32`, que es la pasarela de la red. Pero según cómo publique
Docker Desktop los puertos en Windows, la IP de origen que vea el contenedor podría ser otra. Y dentro
de un contenedor Linux no existe `netsh`, así que todos los bloqueos serían `LOGICAL_BLOCK_ONLY`.

**Cómo lo comprobaría.** Levantando el compose, abriendo el panel y mirando en la bóveda qué IP de origen
registra el contenedor para las peticiones del panel. Si no es `10.88.0.1`, se ajusta la variable.

## 8. Un banco de pruebas, no un atacante real

Este último punto no es un fallo del código, sino un límite de lo que demuestran las pruebas.

El enjambre de Parrot es un script. Sus User-Agents dicen "CrewAI" y "AutoGPT" porque yo los escribí así,
y sus pausas de 1.4 y 1.8 segundos son `sleep` de bash, no tiempo de inferencia de un modelo. Las pruebas
demuestran que **el laboratorio reacciona correctamente** a un tráfico con esas características: detecta
la transferencia del token, mide la cadencia, aplica el tarpit, perita y bloquea.

Lo que no demuestran es cómo se comportaría frente a un enjambre real, que no declarara su framework en el
User-Agent y que variara sus tiempos. Contra un atacante así, el indicador del User-Agent no serviría de
nada, y la cadencia sería más difícil de interpretar. El indicador que seguiría funcionando es el más
fuerte de todos: el Canary Token. Un agente que use un token que recibió otro cliente se delata, diga lo
que diga su User-Agent.

La siguiente prueba honesta de este laboratorio sería esa: ponerlo delante de agentes reales, construidos
con frameworks reales, en una red aislada, y medir qué detecta y qué no.

## El plan para la versión 1.4

Con todo lo anterior, la siguiente versión ya está diseñada:

1. Decaimiento del puntaje del tarpit y limpieza de huellas inactivas.
2. Una sola conexión DuckDB en el gateway; el perito y el servidor MCP piden los datos al gateway.
3. Etiqueta `CANARY_MINTED` en la emisión del token.
4. Fusión de los dos indicadores de transferencia.
5. Firma digital o sello de tiempo para el acta.
6. Neutralización del contenido remoto en las herramientas MCP.
7. Prueba completa del despliegue en Docker.
8. Pruebas contra agentes reales en una red aislada.

Y una regla para cuando esa versión exista: se prueba con el mismo campo de tiro de Parrot, se compara
su acta con la de esta versión, y solo la sustituye si detecta lo mismo o más sin perder ninguna de las
salvaguardas.

## Lo que te llevas de aquí

- Documenta los fallos de tu sistema de defensa con el mismo cuidado que sus aciertos: quien lo use
  necesita saber dónde no fiarse.
- Dos fallos son de rendimiento y de memoria (el puntaje que no olvida y la conexión por petición), y
  solo aparecieron al medir.
- Dos son de forma en el acta (la etiqueta del Scout y los indicadores duplicados), y uno de alcance (el
  hash no prueba autoría).
- El más serio es el del asistente MCP, que lee evidencia escrita por el atacante y puede bloquear IPs.
- Docker está corregido pero no probado, y así hay que decirlo.
- Las pruebas demuestran cómo reacciona el laboratorio a un tráfico con forma de enjambre, no cómo
  rendiría contra uno real. El Canary Token es el indicador que seguiría funcionando.
