# Apéndice B — Glosario

**Acta forense.** Documento que exporta el laboratorio con el resumen de sesiones, el linaje de
enjambres, los dictámenes y el estado de contención, sellado con SHA-256.

**Agente de IA.** Programa que usa un modelo de lenguaje para decidir qué hacer a partir de lo que lee:
llama a herramientas, interpreta respuestas y encadena pasos.

**Cadencia.** En este libro, la mediana de los tiempos entre peticiones consecutivas de una misma huella,
contando solo los que caen entre 0 y 30 segundos.

**Canary Token.** Señuelo que deja una marca en quien lo toca. Aquí, un token firmado que lleva la
identidad del cliente que lo recibió.

**CORS** (*Cross-Origin Resource Sharing*). Regla que aplican los navegadores para decidir qué páginas
pueden leer las respuestas de un servidor. No es autenticación: no afecta a `curl` ni a scripts.

**Defensa en profundidad.** Diseño en el que varias capas independientes protegen lo mismo, para que el
fallo de una no abra el sistema.

**DuckDB.** Base de datos embebida y columnar que vive en un solo archivo. Aquí guarda toda la evidencia.

**Enjambre** (*swarm*). Varios agentes que se reparten un ataque. En su forma más simple, un Scout que
explora y un Exploit que ataca con lo que el Scout encontró.

**Entropía de Shannon.** Medida del desorden de un texto, en bits por símbolo. Sube con el número de
símbolos distintos y lo repartidos que están.

**Exploit.** En este libro, el papel del enjambre que ataca usando lo que encontró el Scout.

**FastAPI.** Framework de Python para construir APIs web. Aquí, el gateway del laboratorio.

**FastMCP.** Forma abreviada de declarar un servidor MCP en Python con decoradores.

**Gateway.** El servidor por el que entra todo el tráfico: el middleware forense, los señuelos y la
superficie de mando.

**Hash encadenado.** Secuencia de hashes en la que cada uno incluye el anterior, de modo que cambiar un
solo elemento altera todos los que vienen detrás.

**HMAC.** Código de autenticación de mensajes basado en un hash y un secreto. Permite verificar que un
dato lo generó quien conoce el secreto.

**Honeypot.** Sistema señuelo diseñado para atraer y observar a un atacante.

**Huella de sesión** (*fingerprint*). Aquí, los primeros 16 caracteres del SHA-256 de IP, User-Agent y
cabecera `X-Swarm-Node`.

**HUD.** El panel del operador, en Angular 19.

**Inyección de comandos.** Ataque que consigue que un programa ejecute comandos del sistema introduciendo
texto en un dato que se pasa al shell.

**Inyección indirecta de instrucciones.** Ataque contra un modelo de lenguaje que esconde instrucciones en
contenido que el modelo va a leer, como una evidencia o un documento.

**LM Studio.** Aplicación de escritorio para ejecutar modelos de lenguaje locales con una API compatible
con la de OpenAI.

**Loopback.** La interfaz de red que apunta a la propia máquina: `127.0.0.1` en IPv4 y `::1` en IPv6.

**MCP** (*Model Context Protocol*). Estándar con el que los asistentes de IA descubren y usan herramientas
externas.

**Mediana.** El valor central de un conjunto ordenado. A diferencia de la media, apenas le afectan los
valores extremos.

**Middleware.** Función que se ejecuta antes de cada petición, sea cual sea su ruta.

**NAT de WSL.** Modo de red por defecto de WSL2, en el que la distribución Linux vive en su propia red
privada detrás de una interfaz virtual de Windows.

**netsh.** Herramienta de línea de comandos de Windows para gestionar, entre otras cosas, el firewall.

**Perito.** El componente que clasifica cada sesión y redacta el dictamen. Aquí, híbrido: Python decide y
un modelo local comenta.

**Scout.** En este libro, el papel del enjambre que explora y recoge información.

**SOAR** (*Security Orchestration, Automation and Response*). Respuesta automatizada a incidentes. Aquí,
el bloqueo en Windows Firewall.

**Superficie de mando.** Las rutas que controlan el laboratorio: telemetría y acciones.

**Tarpit.** Defensa que retrasa las respuestas a los clientes sospechosos para que atacar sea caro.

**Transferencia lateral** (`LATERAL_SWARM_HANDOFF`). Uso de un Canary Token por una huella distinta de la
que lo recibió. Es la prueba de que hay un enjambre.

**WSL2** (*Windows Subsystem for Linux*). Capa de Windows que ejecuta distribuciones Linux en una máquina
virtual ligera.
