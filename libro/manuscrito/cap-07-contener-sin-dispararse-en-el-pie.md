# Capítulo 7 — Contener sin dispararse en el pie

> Borrador. Fuente: backend/soar.py, backend/session_queries.py, backend/main.py, frontend (hub.component.ts),
> logs/bitacora.md (6 de noviembre de 2026, entradas de las 14:42, 15:13 y 15:18) y el acta final.

Hasta aquí, el laboratorio observa, engaña y retrasa. Ahora toca actuar: sacar al atacante de la red.
En el mundo de la seguridad, a este tipo de respuesta automatizada se le llama **SOAR**
(*Security Orchestration, Automation and Response*): orquestar, automatizar y responder.

Es la parte del sistema con más poder y, por eso, la que más fácil se vuelve contra ti. Un bloqueo
mal aplicado puede cortar tu propio panel de control, el router de tu red o el servicio que estás
protegiendo. Y una función de bloqueo que acepta lo que le llega sin mirarlo es una puerta para que
el atacante ejecute comandos en tu máquina.

Este capítulo construye la contención en un solo módulo, `backend/soar.py`, con cinco salvaguardas.
Cada una existe porque evita una forma concreta de dispararse en el pie.

## Una sola implementación

Lo primero es la regla del capítulo 2. Antes de la revisión, el bloqueo estaba escrito dos veces: una
en el gateway, para el botón del panel, y otra en el servidor MCP, para los asistentes de IA. Las dos
copias se parecían, pero no eran iguales. La del servidor MCP, por ejemplo, escribía en la bóveda
lanzando dos sentencias SQL con parámetros en una sola llamada, una forma que nunca se había probado y
que la del gateway no usaba.

Ahora las dos llamadas usan la misma función:

```python
def apply_block(ip_str: str, session_fingerprint: str, reason: str, rule_prefix: str = "VERTEX_BLOCK") -> dict:
```

El gateway la llama con el prefijo `VERTEX_BLOCK` y el servidor MCP con `VERTEX_MCP_BLOCK`, para
saber después en el firewall quién creó cada regla. Todo lo demás es idéntico. Si mañana hay que
corregir algo en el bloqueo, se corrige una vez.

## Salvaguarda 1: nada llega al shell sin validar

La función termina ejecutando `netsh`, el comando de Windows para gestionar el firewall. Y ejecutar un
comando del sistema con datos que vienen de fuera es exactamente lo que buscan los ataques de
inyección de comandos. Si la IP llegara al shell sin validar, un atacante podría mandar algo como
`1.2.3.4; whoami` y conseguir que el servidor ejecutara `whoami`, o algo bastante peor.

La defensa tiene dos capas. La primera es **validar la IP con el parser de la librería estándar**:

```python
def validate_target_ip(ip_str: str) -> str:
    try:
        ip = normalize_ip(ip_str)
    except ValueError:
        raise SoarValidationError(f"'{ip_str}' no es una dirección IP válida.")
    if ip.is_unspecified or ip.is_multicast or str(ip) == "255.255.255.255":
        raise SoarValidationError(f"La IP {ip} no es un objetivo de bloqueo válido.")
    return str(ip)
```

`ipaddress.ip_address` no intenta limpiar la entrada ni adivinar qué quisiste decir: o la cadena
entera es una IP, o lanza un error. `1.2.3.4; whoami` no es una IP, así que nunca pasa de aquí. Y lo
que se usa después no es la cadena original, sino la IP normalizada que devuelve el parser.

La segunda capa es **no usar nunca un shell**. El comando se construye como una lista de argumentos,
no como una cadena:

```python
subprocess.run(["netsh", "advfirewall", "firewall", "add", "rule",
                f"name={rule_name}", "dir=in", "action=block", f"remoteip={valid_ip}"],
               capture_output=True, text=True, timeout=15)
```

Con una lista, Python le pasa cada elemento al programa tal cual, sin que ningún intérprete de comandos
lo lea. Aunque una IP maliciosa llegara hasta aquí, un `;` no significaría nada: sería parte de un
argumento, no un separador de comandos. Las dos capas juntas son defensa en profundidad: si una
fallara, la otra sigue en pie.

La validación también rechaza tres tipos de dirección que no tiene sentido bloquear: `0.0.0.0` (la
dirección sin especificar), las de multidifusión y la de difusión `255.255.255.255`. Bloquear
cualquiera de ellas tiene efectos raros sobre la red de la máquina, y ninguna es la dirección de un
atacante.

## Salvaguarda 2: no te bloquees a ti mismo

Durante las pruebas locales, todo el tráfico llega desde `127.0.0.1`. Si el operador pulsara "aislar"
sobre una sesión de loopback y la regla llegara al firewall, cortaría la comunicación entre el panel,
el gateway y LM Studio, que viven en la misma máquina. El laboratorio se dejaría ciego a sí mismo.

Por eso la contención trata el loopback aparte:

```python
if normalize_ip(valid_ip).is_loopback:
    status = "SIMULATED_LOOPBACK"
    msg = f"Salvaguarda loopback activa: regla '{rule_name}' registrada en DuckDB y simulada para proteger localhost."
```

La acción se registra en la bóveda, igual que un bloqueo real, pero nunca llega al firewall. El panel
lo muestra como **SIMULADO (LOOPBACK)**, para que nadie lo confunda con una contención efectiva. En el
acta final, las cuatro sesiones de las pruebas locales del 3 de noviembre aparecen con ese estado.

Hay un detalle en `normalize_ip` que merece una línea: algunas pilas de red presentan una IPv4 como
una IPv6 "mapeada", del tipo `::ffff:127.0.0.1`. Para Python, eso no es loopback a menos que se
desenvuelva primero. La función lo hace, para que la salvaguarda no tenga un agujero por una cuestión
de formato.

## Salvaguarda 3: no dupliques reglas

`netsh` no se queja si creas dos reglas con el mismo nombre: simplemente crea dos. Si el operador
pulsa el botón dos veces, o si un asistente MCP pide el mismo bloqueo que ya pidió el operador, el
firewall termina lleno de reglas repetidas, y para quitar el bloqueo hay que borrarlas todas.

Antes de crear una regla, el módulo pregunta si ya existe:

```python
def _rule_exists(rule_name: str) -> bool:
    res = _netsh(["show", "rule", f"name={rule_name}"])
    return res.returncode == 0
```

Si existe, no la crea de nuevo y devuelve el estado `ALREADY_ENFORCED`, que el panel muestra igual que
un bloqueo activo, porque lo es.

## Salvaguarda 4: di la verdad sobre lo que pasó

Un bloqueo puede no llegar al firewall por dos motivos. Si el gateway no corre como Administrador,
Windows rechaza la regla. Y si el laboratorio corre dentro de un contenedor Linux, ni siquiera existe
`netsh`. En los dos casos, el código antiguo informaba de un bloqueo, guardaba la acción en la bóveda y
dejaba que el panel mostrara "regla activa". El atacante seguía entrando, y el operador creía haberlo
sacado.

Ahora, cada resultado tiene su propio estado:

| Estado | Qué significa |
|---|---|
| `ENFORCED_NETSH` | La regla se creó en Windows Firewall |
| `ALREADY_ENFORCED` | La regla ya existía; no se duplica |
| `SIMULATED_LOOPBACK` | El objetivo era la propia máquina: se registra, no se bloquea |
| `LOGICAL_BLOCK_ONLY` | Solo quedó en la bóveda: sin permisos de Administrador o sin `netsh` |

Y el módulo captura explícitamente el caso de que `netsh` no exista o no responda, en lugar de dejar
que el error tumbe la petición:

```python
except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
    status = "LOGICAL_BLOCK_ONLY"
    msg = f"Regla '{rule_name}' registrada solo en DuckDB: netsh no disponible ({type(exc).__name__})."
```

El panel traduce cada estado a una etiqueta en el botón. Si dice **SOLO LÓGICO (SIN ADMIN)**, el
operador sabe que tiene que reiniciar el gateway desde una consola de Administrador. Un sistema de
defensa que exagera lo que hizo es peligroso, porque el operador deja de vigilar justo cuando más falta
hace.

## Salvaguarda 5: bloquea al atacante, no a una de sus caras

La última salvaguarda la descubrí en el panel, después de la prueba de fuego. El operador había
aislado al Exploit, `a9101753d8dd5018`, y su tarjeta mostraba **FIREWALL ACTIVO**. Pero las otras
cuatro sesiones de Parrot, el Scout, el Nikto, la comprobación previa y el `curl`, seguían mostrando
el botón rojo de **AISLAR HOST**, como si siguieran sueltas.

No lo estaban. La regla del firewall bloquea por **IP**, no por huella, y las cinco sesiones salían de
la misma IP: `172.28.56.172`. El bloqueo del Exploit las había dejado fuera a todas. Pero el panel
marcaba el bloqueo por huella, así que solo la tarjeta del Exploit se enteraba.

Puede parecer un detalle visual, pero tenía una consecuencia peor: el acta también lo habría registrado
así, con cuatro sesiones de un atacante ya bloqueado marcadas como "sin aislar".

La corrección está en la consulta que comparten el panel y el acta, `session_queries.py`. Además del
bloqueo propio de cada huella, ahora busca los bloqueos reales de su IP:

```sql
WITH ip_block AS (
    SELECT ip_address,
           MAX(rule_name) AS rule_name,
           MAX(enforcement_status) AS enforcement_status
    FROM soar_actions
    WHERE enforcement_status IN ('ENFORCED_NETSH', 'ALREADY_ENFORCED')
    GROUP BY ip_address
)
...
COALESCE(s.rule_name, ib.rule_name, '') AS firewall_rule,
COALESCE(s.enforcement_status, ib.enforcement_status, '') AS enforcement_status
```

Fíjate en el filtro: **solo los bloqueos reales se propagan**. Un bloqueo simulado de loopback no se
extiende a las demás sesiones de `127.0.0.1`; si lo hiciera, todas las sesiones locales aparecerían
como aisladas solo porque alguien pulsó el botón sobre una de ellas.

En el acta final, las cinco sesiones de Parrot aparecen con la misma regla,
`VERTEX_BLOCK_a9101753_172.28.56.172`, en estado `ENFORCED_NETSH`. Es lo que pasó de verdad.

## La prueba de fuego

Con todo esto en su sitio, la secuencia de contención de las pruebas fue la siguiente:

1. El perito clasificó al Exploit `a9101753…` como agente autónomo.
2. El operador pulsó **AISLAR HOST** en su tarjeta.
3. El gateway, ejecutándose como Administrador, creó la regla `VERTEX_BLOCK_a9101753_172.28.56.172` y
   devolvió `ENFORCED_NETSH`. El botón cambió a **FIREWALL ACTIVO**.
4. En Parrot se volvió a lanzar el script de ataque. La comprobación previa no recibió respuesta y el
   script terminó con el mensaje *"No hay respuesta… (timeout o conexión rechazada)"*.

Windows Firewall descartaba en silencio todo lo que llegaba desde la IP de Parrot. Para el atacante, el
servidor había desaparecido.

Para repetir las pruebas, las reglas se retiran con el script de parada, desde una consola de
Administrador en la carpeta del laboratorio:

```powershell
powershell -ExecutionPolicy Bypass -File .\Stop-VertexLab.ps1 -RemoveBlocks
```

## Lo que te llevas de aquí

- La contención es la parte con más poder del sistema y la más fácil de volver contra ti. Vive en un
  solo módulo que comparten el panel y el servidor MCP.
- Nada llega al shell sin pasar por `ipaddress`, y el comando se construye como lista de argumentos,
  nunca como cadena.
- El loopback nunca se bloquea: se registra como `SIMULATED_LOOPBACK` para no dejar ciego al propio
  laboratorio.
- No se duplican reglas, y cada resultado dice la verdad: firewall activo, ya existente, simulado o
  solo lógico.
- El firewall bloquea por IP. El panel y el acta tienen que reflejarlo en todas las sesiones de esa IP,
  pero solo con bloqueos reales.
- En la prueba de fuego, un clic creó la regla real y el atacante dejó de recibir respuesta.
