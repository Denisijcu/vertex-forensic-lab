# Capítulo 9 — Campo de tiro: Parrot contra Windows

> Borrador. Fuente: tmp/swarm_assault.sh, Start-VertexLab.ps1, docker-compose.yml y logs/bitacora.md
> (6 de noviembre de 2026, entradas de las 14:34, 14:42, 14:56, 15:00, 15:03 y 15:13–15:17).

Todo lo de los capítulos anteriores se puede probar desde la propia máquina, con `curl` contra
`localhost`. Así se probó el laboratorio en sus primeras versiones, y así funcionaba. Pero probar por
loopback tiene dos problemas que solo se ven cuando dejas de hacerlo.

El primero ya lo contó el capítulo 8: desde la propia máquina, la superficie de mando **tiene** que
responder, así que nunca descubres que también responde a los demás. El segundo es que, por loopback,
todos los bloqueos son simulados. Puedes pulsar "aislar" cien veces y no sabrás nunca si una regla
real de firewall corta al atacante.

Para saberlo hace falta un atacante de verdad, en otra máquina, en otra red. Este capítulo monta ese
campo de tiro dentro del mismo portátil, con WSL y Parrot, y repasa las cuatro rondas de pruebas, con
sus errores incluidos.

## Dos redes en una máquina

WSL2 ejecuta las distribuciones Linux dentro de una máquina virtual ligera. En su modo de red por
defecto, el **NAT**, esa máquina virtual vive en su propia red privada, separada de Windows por una
interfaz virtual. En la máquina de las pruebas, esa interfaz era:

```
vEthernet (WSL (Hyper-V firewall))    172.28.48.1 / 20
```

Windows es `172.28.48.1` dentro de esa red, y Parrot recibe otra IP del mismo rango. En las pruebas,
Parrot fue `172.28.56.172`. Cuando Parrot se conecta a `172.28.48.1:8000`, el tráfico cruza la interfaz
virtual y llega a Windows como tráfico de red de verdad: con una IP de origen que no es `127.0.0.1`, y
sujeto a Windows Firewall.

Antes de lanzar nada conviene comprobar tres cosas desde Windows, en una consola normal:

```powershell
Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.InterfaceAlias -like "*WSL*" }
Get-NetTCPConnection -State Listen | Where-Object { $_.LocalPort -in 8000,4200,1234 }
Get-NetFirewallRule | Where-Object { $_.DisplayName -like "VERTEX*" }
```

La primera da la IP y el prefijo de la interfaz de WSL. La segunda dice si los puertos del gateway, del
panel y de LM Studio están libres o ya ocupados. La tercera, si quedan reglas de pruebas anteriores. En
la máquina de las pruebas, LM Studio escuchaba en el 1234, el 8000 y el 4200 estaban libres y no había
ninguna regla `VERTEX`.

Un aviso: si tu WSL usa el modo de red **mirrored** en lugar de NAT, no existe esa interfaz, y Parrot
comparte las direcciones de Windows. En ese caso, el tráfico de Parrot podría llegar como loopback y
caer en la salvaguarda del capítulo 7. El script de arranque lo detecta y lo avisa.

## El conflicto que no se veía

Revisando el `docker-compose.yml` del laboratorio, con la red de WSL ya delante, apareció un conflicto
que habría roto las pruebas sin dar ninguna pista.

La red aislada que el compose creaba para el honeypot y su simulador era esta:

```yaml
ipam:
  config:
    - subnet: 172.28.0.0/16
```

`172.28.0.0/16` abarca todas las direcciones de `172.28.0.0` a `172.28.255.255`. Y la red de WSL,
`172.28.48.0/20`, está **dentro** de ese rango. Si alguien levantaba el compose, Docker creaba una red
que se solapaba con la de WSL, y el tráfico de Parrot hacia Windows podía acabar enrutado hacia la red
de los contenedores. Un error así no da mensajes: simplemente, las conexiones dejan de llegar a donde
deberían.

La corrección fue mover la red de Docker a un rango que no se cruza con nada de la máquina,
`10.88.0.0/24`. La lección general: antes de elegir una subred privada para un proyecto, mira cuáles
usa ya tu máquina. Las redes privadas son pocas y los programas que las eligen "por defecto" son
muchos.

## El script de ataque

El ataque es un script de bash, `tmp/swarm_assault.sh`, que se ejecuta dentro de Parrot. Lo primero que
hace es averiguar a dónde atacar:

```bash
WIN_HOST_IP=$(ip route show default | awk '{ print $3; exit }')
TARGET_URL="${TARGET_URL:-http://${WIN_HOST_IP}:8000}"
```

En el modo NAT, la puerta de enlace por defecto de Parrot es precisamente Windows. El script la lee de
la tabla de rutas y no hay que escribir ninguna IP a mano.

Después hace una **comprobación previa**: una petición a la raíz del servidor, con su propia huella,
para saber si hay alguien escuchando. Si no hay respuesta en 20 segundos, el script termina con un
aviso que, como veremos al final del capítulo, también es un resultado:

```bash
if ! $CURL -o /dev/null -A "Vertex-Precheck/1.3" -H "X-Swarm-Node: precheck" "${TARGET_URL}/"; then
    echo " [!] No hay respuesta de ${TARGET_URL} (timeout o conexion rechazada)."
    echo "     Si ya aislaste esta IP con el SOAR, ESTE es el resultado esperado."
    exit 1
fi
```

Y luego lanza las cuatro fases:

1. **Escáner clásico.** Tres sondeos a la bóveda con el User-Agent de Nikto, sin pausas.
2. **Scout.** Una petición a la trampa con el User-Agent de CrewAI. Extrae el Canary Token de la
   respuesta y espera 1.8 segundos, simulando la coordinación del enjambre.
3. **Exploit.** Tres ataques a la bóveda con el User-Agent de AutoGPT y LangGraph, cada uno con el
   token robado y una inyección SQL distinta, con 1.4 segundos entre uno y otro.
4. **Superficie de mando.** El mismo Exploit pide la telemetría e intenta crear un bloqueo.

Todos los `curl` llevan un límite de 20 segundos, para que un servidor bloqueado produzca un timeout en
lugar de dejar la terminal colgada.

## Copiarlo bien: los finales de línea

El script vive en el disco de Windows, y Parrot lo ve en `/mnt/e/vertex-forensic-lab/tmp/`. Pero un
archivo editado en Windows puede tener finales de línea de Windows (`\r\n`), y bash no los entiende: el
`\r` se cuela en cada comando y produce errores absurdos. La forma segura de ejecutarlo es copiarlo a
Parrot quitando los `\r` por el camino:

```bash
tr -d '\r' < /mnt/e/vertex-forensic-lab/tmp/swarm_assault.sh > /tmp/swarm_assault.sh
bash /tmp/swarm_assault.sh
```

Ese paso tiene una consecuencia que pisé en la segunda ronda: si cambias el script en Windows y te
saltas el `tr`, en `/tmp` sigue estando la versión anterior.

## Ronda 1: el tráfico cruza la red

En la primera ronda, el panel mostró por primera vez sesiones con una IP que no era `127.0.0.1`. Las
tres de Parrot llegaron desde `172.28.56.172`: el Nikto, con tres peticiones y 3.992 bits de entropía;
el Scout, con su petición a la trampa; y el Exploit, con 5.692 bits y tres transferencias del token en
el panel de linaje.

Había un detalle raro: la tarjeta del Exploit decía **2 peticiones**, pero el panel de linaje mostraba
**3 transferencias**. No era un error del laboratorio, sino del momento en que miré. El middleware
registra la transferencia en cuanto llega la petición, pero guarda la evidencia **después** de que el
tarpit suelta la respuesta, y en ese punto el tarpit retenía cada petición unos 6 segundos. Miré el
panel mientras la tercera petición estaba todavía retenida.

## Ronda 2: el script equivocado

En la segunda ronda, la consola de Parrot mostró un script de **tres** fases, no de cuatro. Era la
versión antigua, la que había creado una guía anterior en `/tmp`, porque me salté el paso del `tr`. La
fase de la superficie de mando, que era justo lo que quería probar, no se ejecutó.

Esa ronda dejó, sin embargo, un dato valioso: los tres impactos del Exploit tardaron unos 6.4 segundos
cada uno, incluido el primero. Esperaba que el primero tardara menos, unos 3.3 segundos, como en la
ronda anterior. El capítulo 5 explica por qué no fue así: el puntaje del tarpit no baja mientras el
gateway sigue en marcha, y el Exploit, con la misma huella, heredó los puntos de la ronda 1.

## Ronda 3: las cuatro fases

Con el script copiado bien, la tercera ronda imprimió lo esperado, fase por fase:

```
[1/4] Rafaga de escaner estatico (Nikto)...
    -> Probe #1 | HTTP 500 | Tiempo: 0.193003s
    -> Probe #2 | HTTP 500 | Tiempo: 0.205654s
    -> Probe #3 | HTTP 500 | Tiempo: 0.194995s

[2/4] Nodo Scout IA (CrewAI-Recon-Scout/3.1)...
    [+] Canary Token exfiltrado: vx_cnry_NTIwY2M2ZjhkYjMyN2U3...

[3/4] Exploit polimorfico (AutoGPT-Swarm-Exploit/4.0)...
    -> Impacto #1 | HTTP 200 | Tiempo (incluye Tarpit): 6.388919s
    -> Impacto #2 | HTTP 200 | Tiempo (incluye Tarpit): 6.377003s
    -> Impacto #3 | HTTP 200 | Tiempo (incluye Tarpit): 6.389591s

[4/4] Intento de abuso de la superficie SOAR desde la red WSL...
    -> GET  /api/telemetry/state        | HTTP 403 (esperado 403)
    -> POST /api/actions/firewall-block | HTTP 403 (esperado 403)
```

El Nikto recibe el error 500 de la bóveda señuelo, que finge un fallo del controlador de base de datos,
en unos 0.2 segundos. El Exploit recibe un 200 con un "volcado parcial" falso, el premio que le hace
creer que la inyección funcionó, pero cada uno le cuesta 6.4 segundos. Y la superficie de mando le
responde con dos 403.

## El peritaje y sus errores

Con el tráfico de Parrot en la bóveda llegó el primer peritaje con datos reales, y con él los tres
fallos del perito que contó el capítulo 6: el Nikto clasificado como agente por la media de sus Δt, el
`curl` de la antigua comprobación previa clasificado como agente por tocar la trampa, y los dos errores
400 de LM Studio mientras cargaba el modelo. Se corrigió el perito y se cambió la comprobación previa
del script para que no tocara la trampa.

El siguiente peritaje clasificó las cuatro sesiones nuevas sin errores: el Scout y el Exploit como
agentes autónomos, el Nikto y la nueva comprobación previa como escáneres tradicionales.

## Ronda 4: la prueba de fuego

Quedaba la pregunta que justificaba todo el campo de tiro: ¿una regla real de firewall saca de verdad
al atacante?

Con el gateway corriendo como Administrador, en el panel se pulsó **AISLAR HOST** sobre la tarjeta del
Exploit. El gateway creó la regla `VERTEX_BLOCK_a9101753_172.28.56.172` y el botón pasó a **FIREWALL
ACTIVO**. Y en Parrot se volvió a lanzar el ataque:

```
==================================================================
 [*] ASALTO DE ENJAMBRE DESDE PARROT OS (WSL2)
 [*] IP Atacante (Parrot WSL) : 172.28.56.172
 [*] Objetivo (Windows)       : http://172.28.48.1:8000
==================================================================
 [!] No hay respuesta de http://172.28.48.1:8000 (timeout o conexion rechazada).
     Si ya aislaste esta IP con el SOAR, ESTE es el resultado esperado.
```

El script no llegó ni a la primera fase. La comprobación previa esperó sus 20 segundos y no recibió
nada: Windows Firewall descartaba en silencio todo lo que llegaba desde la IP de Parrot. No hubo error
de conexión rechazada ni respuesta de ningún tipo. Para el atacante, el servidor había dejado de
existir.

Ese mensaje es, para mí, la línea más importante de toda la campaña de pruebas. Todo lo demás, la
entropía, el linaje, el perito, el acta, existe para poder llegar a ella con la certeza de que el que
queda fuera es el atacante y no tú.

## Para repetirlo

Las reglas de bloqueo sobreviven al reinicio del laboratorio. Para dejar la máquina como estaba y poder
repetir el campo de tiro, desde una consola de Administrador en `E:\vertex-forensic-lab`:

```powershell
powershell -ExecutionPolicy Bypass -File .\Stop-VertexLab.ps1 -RemoveBlocks
```

Y si además quieres retirar la regla de entrada de WSL:

```powershell
powershell -ExecutionPolicy Bypass -File .\Stop-VertexLab.ps1 -RemoveBlocks -RemoveIngress
```

Recuerda que el puntaje del tarpit vive en memoria: reiniciar el gateway lo pone a cero, y es la única
forma de repetir una ronda en las mismas condiciones que la primera.

## Lo que te llevas de aquí

- Probar solo por loopback esconde dos cosas: que la superficie de mando responde a los demás y que
  los bloqueos nunca son reales. Hace falta un atacante en otra red.
- WSL2 en modo NAT da esa otra red dentro del mismo portátil: Windows en `172.28.48.1`, Parrot en
  `172.28.56.172`.
- Antes de elegir una subred privada, mira las que ya usa la máquina. La red de Docker
  `172.28.0.0/16` se habría tragado la de WSL.
- Copia el script de Windows a Linux quitando los `\r`, o ejecutarás una versión vieja, o una que no
  funciona.
- La evidencia se guarda después del tarpit: un panel mirado a mitad del ataque puede ir por detrás del
  linaje.
- La prueba de fuego es un timeout: después del bloqueo, el atacante no recibe ninguna respuesta.
