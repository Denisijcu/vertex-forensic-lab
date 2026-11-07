# Capítulo 4 — Una trampa con firma

> Borrador. Fuente: backend/swarm_canary.py, backend/main.py (señuelos y middleware),
> logs/bitacora.md (6 de noviembre de 2026, entradas de las 14:42 y 15:25) y el acta final.

Las tres medidas del capítulo anterior describen a cada cliente por separado. Son útiles, pero dejan
sin resolver la pregunta central de este libro: ¿cómo sabes que dos clientes distintos son en
realidad dos partes del mismo atacante?

Podrías intentar adivinarlo por coincidencias: misma IP, peticiones cercanas en el tiempo, rutas
relacionadas. Pero las coincidencias se discuten. Lo que este capítulo construye es una prueba que
no se discute: una trampa que deja una marca criptográfica en quien la toca, de modo que si esa
marca aparece después en manos de otro, la relación entre los dos queda demostrada.

En seguridad, a este tipo de señuelo se le llama **Canary Token**, por los canarios que los mineros
bajaban a las minas: si el canario dejaba de cantar, había gas. Aquí, si el canario aparece donde no
debe, hay un enjambre.

## La trampa: una configuración olvidada

Un Scout busca lo que un administrador olvidó proteger. Así que el señuelo tiene que parecer
exactamente eso. El endpoint `/api/v1/system/config` responde como respondería una ruta de
configuración que alguien dejó abierta en un entorno de pruebas:

```python
@app.get("/api/v1/system/config")
async def trap_system_config(request: Request):
    canary = mint_canary_token(request.state.session_fp, request.state.client_ip)
    return {
        "service": "vertex-core-gateway",
        "environment": "staging-internal",
        "vault_endpoint": "/api/v2/internal/vault",
        "debug_token_hint": canary,
    }
```

Cada campo está pensado para un lector concreto. `environment: staging-internal` sugiere un entorno
de pruebas, donde la seguridad suele ser más laxa. `vault_endpoint` le dice al Scout a dónde ir
después. Y `debug_token_hint` le ofrece justo lo que busca: un token que parece una credencial de
depuración que nadie quitó.

Para un agente de IA, esta respuesta es irresistible, porque está diseñada para ser legible.
Contiene pistas en lenguaje natural que un modelo interpreta sin esfuerzo: "hay una bóveda en esta
ruta, y aquí tienes un token". Un escáner clásico también la recorre, porque recorre todo, pero no
hace nada con lo que encuentra. El agente, en cambio, actúa.

## El token: quién, desde dónde y cuándo

El token no es una cadena aleatoria. Lleva dentro la identidad de quien lo recibió:

```python
def mint_canary_token(scout_fingerprint: str, scout_ip: str) -> str:
    ts = int(time.time() * 1000)
    payload = f"{scout_fingerprint}|{scout_ip}|{ts}"
    payload_b64 = base64.urlsafe_b64encode(payload.encode("utf-8")).decode("utf-8").rstrip("=")
    signature = hmac.new(SECRET_KEY, payload_b64.encode("utf-8"), hashlib.sha256).hexdigest()[:16]
    return f"vx_cnry_{payload_b64}.{signature}"
```

El contenido son tres datos: la **huella** del Scout, su **IP** y el **instante** exacto de emisión,
en milisegundos. Se codifican en base64 para que viajen como texto y se firman con **HMAC-SHA256**
usando un secreto que solo conoce el laboratorio. El resultado tiene esta forma:

```
vx_cnry_<huella|ip|instante en base64>.<firma de 16 caracteres>
```

Por eso, en las pruebas, el token que robaba el Scout empezaba siempre igual,
`vx_cnry_NTIwY2M2ZjhkYjMyN2U3...`: es la huella del Scout, `520cc6f8db327e75`, codificada. Lo que
cambiaba en cada ejecución era el instante y, con él, la firma.

¿Por qué firmar? Porque la base64 no es cifrado: cualquiera puede decodificar el token, leer la
huella y fabricar uno nuevo con otra. La firma lo impide. Sin el secreto, nadie puede generar una
firma válida para un contenido distinto, y el laboratorio detecta la manipulación.

## La verificación: el momento en que el enjambre se delata

Cuando una petición llega con una cabecera `Authorization: Bearer vx_cnry_...`, el middleware la
verifica antes de hacer nada más:

```python
raw_part, recv_sig = token_str[8:].split(".", 1)
expected_sig = hmac.new(SECRET_KEY, raw_part.encode("utf-8"), hashlib.sha256).hexdigest()[:16]

if not hmac.compare_digest(recv_sig, expected_sig):
    return {"status": "TAMPERED_CANARY", "lateral_movement": True}
```

Dos detalles importan aquí. El primero es `hmac.compare_digest`, que compara las firmas en tiempo
constante. Una comparación normal con `==` se detiene en el primer carácter distinto, y eso deja
medir cuánto tarda en fallar para adivinar la firma carácter a carácter. `compare_digest` tarda
siempre lo mismo. El segundo detalle es que una firma que no cuadra no se ignora: se marca como
`TAMPERED_CANARY`. Alguien intentó falsificar el token, y eso también es evidencia.

Si la firma es válida, el laboratorio decodifica el contenido y hace la comparación que da sentido a
toda la trampa:

```python
handoff_type = (
    "LATERAL_SWARM_HANDOFF"
    if scout_fp != current_fp
    else "SINGLE_AGENT_REPLAY"
)
```

Si la huella que **presenta** el token es distinta de la huella que lo **recibió**, el token ha
cambiado de manos. Eso es una **transferencia lateral**: un cliente encontró algo y se lo pasó a
otro. Es la firma de un enjambre, y el laboratorio la registra como `LATERAL_SWARM_HANDOFF`. Si es la
misma huella, el cliente se limita a reutilizar lo que encontró (`SINGLE_AGENT_REPLAY`), lo que es
sospechoso pero no prueba coordinación.

Y como el token lleva el instante de emisión, el laboratorio puede calcular algo más: cuánto tardó
el token en ir de un cliente al otro.

```python
transit_ms = float(now_ms - int(mint_ts_str))
```

Ese **tiempo de tránsito** se guarda en la tabla `swarm_lineage`, junto con las dos huellas, las dos
IPs y la ruta atacada. Es el registro que dibuja el panel rojo del HUD, con cada flecha de Scout a
Exploit.

## El bug del canario falsificado

Revisando el middleware antes de las pruebas encontré un error que convertía una evidencia en una
caída del servidor.

La función de verificación devuelve dos tipos de resultado: uno completo cuando la firma es válida,
con la huella del Scout, el tipo de transferencia y el tránsito, y uno mínimo cuando la firma no
cuadra, con solo `status: TAMPERED_CANARY`. El middleware, sin embargo, trataba los dos igual:

```python
if trace:
    deception_tag = trace["handoff_type"]
```

Ante un token manipulado, `trace` existe pero no tiene la clave `handoff_type`. Python lanza un
`KeyError`, el middleware se cae y el cliente recibe un error 500. Es decir: **el atacante que
intentaba falsificar un token recibía como premio la caída de la petición, y la evidencia de la
falsificación no llegaba a guardarse.**

La corrección distingue los dos casos explícitamente:

```python
if trace and trace.get("status") == "TAMPERED_CANARY":
    deception_tag = "TAMPERED_CANARY"
    tarpit_engine.register_anomaly(fp, weight=3)
elif trace and trace.get("status") == "VALID_CANARY_TRIGGER":
    deception_tag = trace["handoff_type"]
    tarpit_engine.register_anomaly(fp, weight=3)
    # ... y se inserta la fila en swarm_lineage
```

La lección va más allá de este caso: **en un sistema de defensa, cada camino de error es una
superficie de ataque.** El camino feliz se prueba siempre. El camino del atacante que hace algo
inesperado, como manipular el token que le diste, es el que se olvida.

## El secreto, fuera del código

Hay otro detalle que cambió en la revisión. El secreto con el que se firman los tokens estaba
escrito en dos sitios: como valor por defecto en el código y en claro en el archivo
`docker-compose.yml`. Cualquiera con acceso al repositorio podía leerlo y, con él, fabricar tokens
válidos con la huella que quisiera.

Ahora el secreto vive solo en el archivo `.env`, que no se sube a git ni entra en el paquete de
release. El script de arranque lo genera la primera vez, con 32 bytes aleatorios. Y si por algún
motivo no existe, el laboratorio no vuelve a un valor fijo: genera uno efímero para ese proceso y lo
avisa por consola.

```python
_secret = os.environ.get("VERTEX_CANARY_SECRET", "").strip()
if not _secret:
    _secret = secrets.token_hex(32)
    print("[!] VERTEX_CANARY_SECRET no definido: usando secreto efímero. "
          "Ejecuta Start-VertexLab.ps1 para generar .env.", file=sys.stderr)
```

Un secreto efímero tiene un coste: los tokens emitidos antes de reiniciar dejan de verificarse
después. Para un laboratorio es un coste aceptable. Un secreto conocido por todos no lo es.

## Lo que registró la trampa

En las pruebas desde Parrot, el Scout pidió la configuración, recibió el token y, tras una espera de
1.8 segundos que simula la coordinación entre agentes, el Exploit lo presentó en cada uno de sus
tres ataques a la bóveda. El script se lanzó cuatro veces con éxito antes del bloqueo final, y cada
ejecución dejó tres transferencias.

En total, el acta registra **12 transferencias** de `520cc6f8db327e75` (Scout) a
`a9101753d8dd5018` (Exploit), con tiempos de tránsito que van de **1812 ms a 17 487 ms**. El patrón
dentro de cada ejecución se repite: el primer impacto llega a unos 1.8 segundos del robo, el segundo
entre 6.9 y 9.7 segundos, el tercero entre 14.7 y 17.5 segundos. Cada salto es la espera del script
entre impactos más el retraso que el tarpit, del próximo capítulo, añade a cada respuesta.

Esas 12 filas son la prueba más fuerte de todo el acta. No dependen de umbrales, de medias ni de
interpretaciones. Dicen: este cliente recibió un token firmado con su identidad, y este otro cliente
lo presentó. Ningún escáner hace eso.

## Lo que te llevas de aquí

- Un Canary Token es un señuelo que deja una marca en quien lo toca. Si la marca aparece en otras
  manos, la relación entre los dos clientes queda probada.
- El señuelo tiene que parecer un descuido real y legible para un modelo: una configuración de
  pruebas con una pista y un token de depuración.
- El token lleva la huella, la IP y el instante de emisión, codificados en base64 y firmados con
  HMAC-SHA256. La firma se compara en tiempo constante.
- Si la huella que presenta el token no es la que lo recibió, hay una transferencia lateral, la
  firma de un enjambre. El instante de emisión da el tiempo de tránsito.
- Cada camino de error es una superficie de ataque: un token falsificado tumbaba el middleware hasta
  que se trató como evidencia (`TAMPERED_CANARY`).
- El secreto vive solo en `.env`. Sin él, se usa uno efímero, nunca uno fijo.
