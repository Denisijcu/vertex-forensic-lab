# Capítulo 8 — Que no te usen el escudo

> Borrador. Fuente: backend/lab_env.py, backend/main.py (middleware y CORS), backend/telemetry_api.py,
> Start-VertexLab.ps1, logs/bitacora.md (6 de noviembre de 2026, entradas de las 14:34, 14:42 y 15:03) y el acta final.

De todos los problemas que encontré al revisar el laboratorio, este fue el más grave. No era un error
de cálculo ni una etiqueta mal puesta. Era un fallo de diseño que convertía el sistema de defensa en
un arma para el atacante.

Este capítulo lo cuenta entero: cómo era el hueco, por qué nadie lo había visto, cómo se cerró con
cuatro medidas que se refuerzan entre sí y cómo se comprobó desde Parrot que el cierre aguantaba.

## El hueco

Recuerda la superficie de mando del capítulo 2: las rutas `/api/telemetry/*`, que alimentan el panel,
y `/api/actions/*`, que ejecutan el perito, exportan el acta y, sobre todo, **crean reglas de bloqueo
en el firewall**.

Antes de la revisión, esas rutas:

- **no pedían ningún tipo de autenticación**;
- tenían CORS configurado para **cualquier origen** (`*`);
- y el middleware forense las **excluía del registro**, para que el refresco del panel no llenara la
  bóveda de ruido.

Por sí solo, eso podía parecer aceptable en un laboratorio que corre en la máquina del operador. El
problema aparecía al combinarlo con la guía de pruebas, que pedía exactamente lo necesario para atacar
desde Parrot:

- arrancar el gateway **como Administrador**, para que los bloqueos llegaran al firewall;
- hacerlo escuchar en **`0.0.0.0`**, todas las interfaces, para que el tráfico de WSL llegara;
- y crear una regla de entrada que **abría el puerto 8000 a cualquier IP**.

Con esas tres condiciones, cualquier máquina que pudiera alcanzar el puerto 8000 podía hacer esto:

```bash
curl -X POST http://<servidor>:8000/api/actions/firewall-block \
     -H "Content-Type: application/json" \
     -d '{"ip_address":"<la IP de tu router>","session_fingerprint":"x"}'
```

Y el laboratorio, con privilegios de Administrador, habría creado obedientemente una regla en Windows
Firewall que bloqueara el router, el DNS o el propio equipo del operador. Sin que quedara rastro en la
bóveda, porque esas rutas no se registraban.

El atacante no tenía que romper nada. Solo tenía que pedirle al escudo que se volviera contra su dueño.

## Por qué nadie lo vio

Porque todas las pruebas anteriores se habían hecho desde la propia máquina, por `127.0.0.1`. Desde
ahí, la superficie de mando **tenía** que responder: es como el panel habla con el gateway. Nadie
había mirado el sistema desde el otro lado de la red, porque hasta entonces no había otro lado.

Es una lección que vale para cualquier herramienta de seguridad: **las herramientas de defensa son
objetivos.** Un sistema que puede bloquear IPs, borrar archivos, cerrar procesos o cambiar
configuraciones tiene que defenderse a sí mismo antes que a nada. Y la pregunta que hay que hacerse no
es "¿funciona?", sino "¿qué pasa si esta función la llama otra persona?".

## Medida 1: solo responde a quien está en la máquina

La primera medida es la más simple y la más fuerte: la superficie de mando solo responde a peticiones
que vienen de la propia máquina. La política vive, como todo lo demás, en `lab_env.py`:

```python
def is_admin_client(ip_str: str) -> bool:
    try:
        ip = normalize_ip(ip_str)
    except ValueError:
        return False
    if ip.is_loopback:
        return True
    return any(ip in net for net in ADMIN_ALLOWED_NETS)
```

Loopback siempre está permitido. Cualquier otra red tiene que declararse explícitamente en la variable
`VERTEX_ADMIN_ALLOWED_CIDRS`, que por defecto está vacía. El único caso en que hace falta es el
despliegue en Docker, donde el panel del anfitrión llega al contenedor a través de la pasarela de la
red puente. En Windows, con todo en la misma máquina, no se toca.

Fíjate en que la política es una **lista de permitidos**, no de prohibidos. No dice "bloquea a Parrot";
dice "solo deja pasar a la máquina local". Cualquier origen que no se haya previsto queda fuera por
defecto, incluido el que todavía no se te ha ocurrido.

## Medida 2: dos controles, no uno

La política se aplica en dos sitios. El primero es el middleware, antes que cualquier otra cosa:

```python
is_admin_path = path.startswith(ADMIN_PREFIXES)

if is_admin_path and is_admin_client(client_ip):
    return await call_next(request)
```

Si la petición es del panel local, pasa sin dejar rastro en la bóveda, como antes. Si viene de fuera,
el middleware la corta, como veremos en la medida siguiente.

El segundo control es una dependencia de FastAPI que llevan todas las rutas de la superficie de mando,
tanto el router de la telemetría como cada acción:

```python
def require_admin_client(request: Request) -> None:
    client_ip = request.client.host if request.client else ""
    if not is_admin_client(client_ip):
        raise HTTPException(status_code=403, detail="Forbidden")

router = APIRouter(dependencies=[Depends(require_admin_client)])

@app.post("/api/actions/firewall-block", dependencies=[Depends(require_admin_client)])
```

¿Por qué repetir el control si el middleware ya lo aplica? Porque los middlewares se tocan. Alguien
puede añadir una excepción, cambiar el orden o reescribir la función para resolver otra cosa, y abrir
el hueco sin darse cuenta. Con la dependencia, cada ruta lleva su propia cerradura. Para abrir la
puerta hay que romper las dos.

## Medida 3: el intento es evidencia

Cortar la petición no basta. En la versión anterior, el abuso de la superficie de mando no dejaba
rastro. Ahora, cuando una petición de fuera llega a esas rutas, el middleware hace tres cosas antes de
responder:

```python
if is_admin_path:
    tarpit_engine.register_anomaly(fp, weight=2)
    tarpit_ms = await tarpit_engine.apply_tarpit_if_needed(fp)
    persist_evidence(now, client_ip, fp, request.method, path, request.url.query, ua,
                     delta_t_ms, entropy, tarpit_ms, "ADMIN_SURFACE_PROBE")
    return JSONResponse(status_code=403, content={"detail": "Forbidden"})
```

**Suma sospecha** en el tarpit, como cualquier otro comportamiento hostil. **Guarda la evidencia** en
la bóveda con la etiqueta `ADMIN_SURFACE_PROBE`. Y solo entonces **responde con un 403** genérico, sin
explicar por qué ni qué esperaba. Al atacante no se le da información; al operador, toda.

## Medida 4: estrechar la red

Las tres medidas anteriores protegen las rutas. La cuarta reduce quién puede llegar al puerto.

La guía antigua creaba una regla de entrada que abría el puerto 8000 a cualquier origen. Ahora, el
script de arranque crea la regla `VERTEX_LAB_INGRESS_8000` **solo para la subred de WSL**, y la calcula
en cada arranque a partir de la interfaz virtual:

```powershell
$wslIf = Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.InterfaceAlias -like "vEthernet (WSL*" }
# ... cálculo de la red a partir de la IP y la longitud del prefijo ...
New-NetFirewallRule -DisplayName $IngressRule -Direction Inbound -Action Allow -Protocol TCP `
    -LocalPort 8000 -RemoteAddress $WslSubnet -Profile Any
```

En la máquina de las pruebas, la interfaz de WSL tenía la IP `172.28.48.1` con un prefijo de 20 bits,
así que la regla quedó acotada a `172.28.48.0/20`. Se recalcula en cada arranque porque, en el modo de
red NAT de WSL, esa subred puede cambiar al reiniciar Windows.

Hay un detalle que conviene saber: en Windows Firewall, una regla de bloqueo **gana** siempre a una de
permiso. Por eso la contención del capítulo 7 funciona aunque exista esta regla de entrada: el
bloqueo de la IP de Parrot pesa más que el permiso para su subred.

## Un apunte sobre CORS

En la misma revisión, CORS pasó de aceptar cualquier origen a aceptar solo el panel local:

```python
HUD_ORIGINS = ["http://localhost:4200", "http://127.0.0.1:4200"]
app.add_middleware(CORSMiddleware, allow_origins=HUD_ORIGINS,
                   allow_methods=["GET", "POST"], allow_headers=["Content-Type"])
```

Pero quiero ser preciso con lo que eso protege, porque es una confusión muy común. **CORS no es
autenticación.** Es una regla que aplican los navegadores: impide que una página de otro sitio, abierta
en el navegador del operador, lea las respuestas del laboratorio. No impide nada a `curl`, a un script
de Python ni a un agente de IA, que simplemente ignoran CORS. Restringirlo cierra un camino concreto, el
de una web maliciosa que use el navegador del operador como puente. La protección de verdad contra el
atacante de la red son las medidas 1 a 3.

## El secreto, también fuera

La última pieza de este capítulo ya apareció en el capítulo 4: el secreto que firma los Canary Tokens
estaba escrito en el código y en el `docker-compose.yml`. Ahora lo genera el script de arranque la
primera vez, con 32 bytes aleatorios, y lo guarda en `.env`:

```powershell
$bytes = New-Object byte[] 32
[System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
$secret = -join ($bytes | ForEach-Object { $_.ToString("x2") })
```

El archivo `.env` está excluido del control de versiones y del paquete de release, y el
`docker-compose.yml` exige que la variable esté definida en lugar de traer un valor propio.

## La comprobación desde Parrot

El script de ataque tiene una cuarta fase dedicada a esto. Después del escáner, del Scout y del
Exploit, el mismo Exploit intenta usar la superficie de mando: pide la telemetría y trata de crear un
bloqueo contra la IP `1.1.1.1`.

Este es el resultado, tal como lo imprimió la consola de Parrot:

```
[4/4] Intento de abuso de la superficie SOAR desde la red WSL...
    -> GET  /api/telemetry/state        | HTTP 403 (esperado 403)
    -> POST /api/actions/firewall-block | HTTP 403 (esperado 403)
```

Dos peticiones, dos 403. Ninguna regla nueva en el firewall. Y en el acta final, la sesión del Exploit
lleva entre sus indicadores de engaño `ADMIN_SURFACE_PROBE`, y su dictamen termina con este contexto:
*"intentó acceder a la superficie de mando SOAR y fue rechazado con 403"*. El intento de usar el
escudo quedó escrito como prueba en contra de quien lo intentó.

## Lo que te llevas de aquí

- Las herramientas de defensa son objetivos. Una API que crea reglas de firewall, abierta a la red y
  sin autenticación, es un arma para el atacante.
- El hueco no se veía porque todas las pruebas se hacían desde la propia máquina. Hay que mirar el
  sistema desde el otro lado de la red.
- La superficie de mando solo responde a loopback, con una lista de permitidos y no de prohibidos.
- Dos controles independientes, middleware y dependencia en cada ruta, para que un cambio en uno no
  abra la puerta.
- El intento de abuso suma sospecha, queda como evidencia (`ADMIN_SURFACE_PROBE`) y recibe un 403 sin
  explicaciones.
- La regla de entrada se acota a la subred de WSL, y CORS solo al panel local, sabiendo que CORS no
  es autenticación.
