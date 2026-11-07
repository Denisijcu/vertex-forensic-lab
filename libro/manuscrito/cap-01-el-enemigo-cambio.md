# Capítulo 1 — El enemigo cambió

> Borrador. Fuente: logs/bitacora.md (6 de noviembre de 2026, entradas de las 15:03, 15:17 y 15:25)
> y reports/ACTA_FORENSE_VERTEX_20261106_152518.md. Todas las cifras de este capítulo están medidas.

Durante años, el tráfico hostil que llegaba a una API tenía una firma reconocible. Un escáner
recorría una lista de rutas, una detrás de otra, a la velocidad que le permitía la red. Probaba
las mismas cargas en el mismo orden, y no cambiaba de estrategia por mucho que le respondieras. Si
el servidor devolvía un error, el escáner seguía con la siguiente línea de su lista. Era ruidoso,
rápido y tonto, y por eso mismo era fácil de reconocer.

Ese atacante sigue existiendo. Pero ahora tiene compañía.

Un agente de IA no recorre una lista: lee. Lee la respuesta del servidor, razona sobre ella y
decide qué hacer después. Si una ruta le devuelve un detalle de configuración, lo apunta. Si un
mensaje de error menciona una base de datos, ajusta la siguiente carga a esa base de datos. Y
cuando varios agentes trabajan juntos, se reparten el trabajo: uno explora y otro ataca con lo que
el primero encontró. A ese conjunto coordinado se le llama **enjambre**.

Este libro trata de cómo reconocer un enjambre cuando llega a tu servidor, de cómo hacerle pagar
cada paso que da, y de cómo sacarlo de tu red con una regla real de firewall. Y de algo más
importante todavía: de cómo dejar constancia de todo eso en un documento que se pueda defender.

## El Scout y el Exploit

La forma más simple de un enjambre tiene dos papeles.

El **Scout** es el explorador. Recorre la superficie de la API con calma, buscando lo que un
administrador olvidó proteger: una ruta de configuración, un endpoint de depuración, una pista en
un mensaje de error. No ataca nada. Solo mira y anota.

El **Exploit** es el ejecutor. No explora: recibe lo que encontró el Scout y lo usa. Si el Scout
descubrió un token, el Exploit lo presenta. Si el Scout encontró una ruta interna, el Exploit la
ataca con cargas pensadas para ella.

Visto desde el servidor, el problema es que son **dos clientes distintos**. Pueden tener
User-Agents distintos, cabeceras distintas, incluso IPs distintas. Un cortafuegos de aplicaciones
que analiza cada petición por separado ve a un visitante curioso y, más tarde, a un atacante con
una credencial. No ve que el segundo está usando lo que encontró el primero. Y esa relación es
justo la prueba de que no se trata de un escáner, sino de un enjambre.

## Lo que vamos a construir

**Vertex Forensic Lab** es un laboratorio que se pone delante de una API y hace cinco cosas:

1. **Mide la física del tráfico.** Cada petición recibe una huella de sesión, una medida de lo
   desordenado que es su contenido (la entropía de Shannon) y el tiempo que pasó desde la petición
   anterior de esa misma huella.
2. **Siembra una trampa con firma.** Un endpoint señuelo entrega un token firmado que identifica a
   quien lo recogió. Si después lo presenta **otra** huella, el enjambre queda probado con
   criptografía, no con sospechas.
3. **Hace que cada pregunta cueste.** Un tarpit retrasa las respuestas a las sesiones sospechosas,
   cada vez más, hasta agotar el presupuesto de tiempo del atacante.
4. **Perita cada sesión.** Un perito clasifica cada huella como agente autónomo o escáner
   tradicional, con indicadores que se pueden verificar uno a uno, y redacta el dictamen.
5. **Contiene y documenta.** Un botón aísla al atacante con una regla real de Windows Firewall, y
   otro exporta un acta forense firmada con SHA-256.

Todo corre en una sola máquina con Windows 11: un gateway en FastAPI, una base de datos DuckDB, un
panel en Angular, un modelo de lenguaje local en LM Studio y un servidor MCP para que un asistente
de IA pueda consultar la evidencia. Y el atacante, para las pruebas, corre en la misma máquina,
dentro de una distribución Parrot en WSL, en su propia red virtual.

## Los resultados, por adelantado

Como en los libros anteriores de esta serie, prefiero enseñarte el final antes que el camino. Así
sabes a dónde vamos y contra qué medir lo que construyas.

La prueba definitiva se hizo atacando el laboratorio desde Parrot, con un script de cuatro fases:
un escáner clásico, un Scout que roba el token, un Exploit que ataca con él y un intento de tomar
el control del propio laboratorio. El tráfico salió de la IP `172.28.56.172`, la de Parrot, y
cruzó la red virtual hasta el servidor en `172.28.48.1`. No pasó por la interfaz local: fue
tráfico de red de verdad.

Esta es la tabla del acta final, tal como la firmó el laboratorio:

| Sesión | Peticiones | Cadencia mediana | Entropía máx. | Veredicto | Contención |
|---|---|---|---|---|---|
| Exploit (AutoGPT / LangGraph) | 16 | 7791.45 ms | 5.716 bits | Agente autónomo, 95 % | Regla real en el firewall |
| Scout (CrewAI) | 4 | 0.0 ms | 3.914 bits | Agente autónomo, 95 % | Bloqueado por IP |
| Escáner (Nikto) | 12 | 223.5 ms | 3.992 bits | Escáner tradicional, 90 % | Bloqueado por IP |
| Comprobación previa del script | 1 | 0.0 ms | 1.0 bits | Escáner tradicional, 90 % | Bloqueado por IP |
| `curl` simple | 1 | 0.0 ms | 3.914 bits | Escáner tradicional, 90 % | Bloqueado por IP |

Y estos son los momentos que la tabla no cuenta:

- **El linaje.** El laboratorio registró 12 transferencias del token del Scout al Exploit, cada una
  con su tiempo de tránsito: desde 1.8 hasta 17.5 segundos entre que el Scout recibió el token y el
  Exploit lo presentó.
- **El tarpit.** El escáner recibía sus respuestas en unos 0.2 segundos. El Exploit, en unos 6.4.
  Cada carga de inyección le costaba treinta veces más tiempo que una petición normal.
- **El intento de tomar el mando.** Desde Parrot, el script pidió la telemetría del laboratorio y
  trató de disparar un bloqueo de firewall contra otra IP. Las dos peticiones recibieron un
  `403`, y las dos quedaron registradas como evidencia en contra del atacante.
- **La contención.** Un clic en el panel creó la regla `VERTEX_BLOCK_a9101753_172.28.56.172` en
  Windows Firewall. Al volver a lanzar el ataque, Parrot ya no recibió respuesta: la conexión murió
  por tiempo de espera.

Detección, linaje, tarpit, peritaje, aislamiento y acta firmada, de punta a punta y con tráfico
real. Ese es el ciclo completo.

## Lo que no salió a la primera

Un libro que solo enseña lo que funcionó no te prepara para lo que te va a pasar a ti. Así que
también te cuento, por adelantado, lo que falló durante las pruebas. Cada uno de estos fallos tiene
su capítulo.

**El escáner que parecía un agente.** En el primer peritaje, el Nikto salió clasificado como
agente autónomo. La razón era una media aritmética: el perito medía el tiempo medio entre
peticiones, y como el escáner había atacado en varias tandas separadas por minutos, esos minutos
inflaron la media hasta 46 381 milisegundos. Parecían las pausas de un modelo pensando. La cadencia
real dentro de cada ráfaga era de 223.5 milisegundos: mecánica pura. El capítulo 3 explica por qué
la mediana dentro de cada ráfaga mide la verdad y la media no.

**La trampa que acusaba a cualquiera.** Un simple `curl` también salió como agente, porque "tocar
la trampa" contaba como indicador. Pero un escáner clásico también toca la trampa: la recorre como
recorre todo lo demás. Lo que prueba un enjambre no es tocarla, sino **usar** el token desde otra
huella. El capítulo 6 separa lo que decide de lo que solo aporta contexto.

**El modelo que firmaba cifras falsas.** El perito usa un modelo local para redactar los dictámenes.
En la primera acta con tráfico real, 7 de sus 9 dictámenes contradecían la evidencia: afirmaba, por
ejemplo, que una entropía de 3.914 bits "supera el umbral" de 4.5. Un documento con sello
criptográfico no puede decir eso. El capítulo 6 cuenta la decisión de diseño que resolvió el
problema, y que resume una de las ideas centrales de este libro: **el modelo puede asistir, pero no
puede dar fe.**

**El escudo que se podía usar contra ti.** Y el más grave, que encontré al revisar el proyecto antes
de las pruebas: la API que dispara los bloqueos de firewall estaba abierta a la red, sin
autenticación. Cualquiera que llegara al puerto podía pedirle al laboratorio que bloqueara la IP de
tu router. Un sistema de defensa que el atacante puede usar a su favor es peor que no tener
ninguno. El capítulo 8 cierra ese hueco.

## Lo que hace falta

Para seguir el libro de principio a fin necesitas:

- **Windows 11** con PowerShell y permisos de Administrador. Sin Administrador, el laboratorio
  funciona igual, pero los bloqueos se quedan registrados en la base de datos y no llegan al
  firewall.
- **Python 3.10 o superior** para el gateway, el perito y el servidor MCP, y **Node.js 20** con
  Angular CLI 19 para el panel.
- **WSL2 con una distribución Linux** para atacar desde fuera. Yo uso Parrot, pero sirve cualquiera
  que tenga `curl` y `bash`.
- **LM Studio**, si quieres que el modelo local comente los dictámenes. Es opcional: sin él, el
  perito sigue clasificando y redactando el dictamen oficial, porque esa parte no depende del
  modelo.

No necesitas servidores en la nube, ni herramientas comerciales, ni un equipo de seguridad. El
laboratorio entero cabe en tu portátil.

## Una nota sobre el enfoque

Este es un libro de **defensa**. El ataque que aparece en sus páginas se lanza desde una máquina
propia, en una red virtual propia, contra un honeypot propio construido para recibirlo. Su único
propósito es comprobar que las defensas funcionan con tráfico real y no solo en teoría.

No vas a encontrar aquí técnicas para atacar sistemas de terceros. Lo que vas a encontrar es cómo
pensar como el que defiende cuando el atacante ya no es un script, sino un modelo.

## Cómo está organizado el viaje

Los capítulos 2 y 3 preparan el terreno: la arquitectura del laboratorio y las medidas sobre las
que se apoya todo lo demás. Los capítulos 4 y 5 construyen las dos defensas activas, la trampa con
firma y el tarpit. El capítulo 6 construye el perito y cuenta por qué el modelo no firma nada.

Los capítulos 7 y 8 tratan de la contención: cómo aislar al atacante sin cortarte a ti mismo, y
cómo impedir que el atacante use tus propias defensas. El capítulo 9 monta el campo de tiro con
Parrot y repasa las cuatro rondas de pruebas, con sus errores. El 10 explica cómo se firma el acta,
el 11 conecta un asistente de IA a la evidencia mediante MCP, y el 12 recoge lo que todavía falla.

Todo el código está en el repositorio del proyecto. Cuando el libro te pida correr un comando, te
dirá también desde qué carpeta y en qué consola: normal o como Administrador. En un laboratorio que
toca el firewall del sistema, esa diferencia importa.

## Lo que te llevas de aquí

- Un enjambre de agentes de IA reparte el trabajo: un Scout explora y un Exploit ataca con lo que
  el Scout encontró. Analizadas por separado, sus peticiones no revelan esa relación.
- Vertex Forensic Lab mide el tráfico, siembra una trampa con firma, frena a los sospechosos,
  perita cada sesión, aísla al atacante y firma un acta con todo.
- En la prueba con tráfico real desde Parrot clasificó bien las cinco sesiones, registró 12
  transferencias del token, rechazó los dos intentos de tomar el mando y dejó al atacante fuera con
  una regla real de firewall.
- Los fallos también se miden: una media engañosa, un indicador que acusaba a cualquiera, un modelo
  que firmaba cifras falsas y una API de bloqueo abierta a la red. Los cuatro se corrigieron, y los
  cuatro tienen su capítulo.
