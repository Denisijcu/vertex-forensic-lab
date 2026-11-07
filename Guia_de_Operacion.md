# GUÍA DE OPERACIÓN — VERTEX FORENSIC LAB v1.3

## 1. Propósito

Vertex Forensic Lab es un sistema de contrainteligencia y observabilidad para arquitecturas expuestas a agentes de IA. Cuando un enjambre autónomo hace reconocimiento con un nodo *Scout* y pasa lo que encuentra a un nodo *Exploit*, un WAF de firmas estáticas no ve la relación entre ambos. El laboratorio sí la ve, porque:

- **Mide la física del tráfico:** entropía de Shannon H(X) de cada petición, pausas Δt entre peticiones y una huella SHA-256 por combinación de IP, User-Agent y nodo de enjambre.
- **Siembra señuelos rastreables:** el endpoint trampa entrega un Canary Token firmado; si otra huella lo presenta después, queda probada la transferencia lateral (`LATERAL_SWARM_HANDOFF`).
- **Perita con doble escudo:** Python decide la clasificación con indicadores duros; el modelo local solo redacta el dictamen en español, y si se contradice con las cifras o responde en inglés, se usa el dictamen determinista.
- **Responde:** aísla hosts con reglas reales de Windows Firewall (`netsh`) desde el HUD o desde un agente MCP.

## 2. Requisitos

| Componente | Detalle |
| --- | --- |
| Sistema | Windows 11 con PowerShell. Administrador para reglas de firewall reales. |
| Python | 3.10+ con `fastapi`, `uvicorn`, `duckdb`, `pydantic`, `httpx`; `mcp` para el servidor MCP. |
| Frontend | Node.js 20+ y Angular CLI 19. |
| LLM local | LM Studio en el puerto `1234` con `vertex-core-sec-turn` (opcional). |
| Atacante | Parrot OS en WSL2 en modo de red NAT (por defecto). |

## 3. Estados de contención SOAR

| Estado | Significado |
| --- | --- |
| `ENFORCED_NETSH` | Regla de bloqueo creada en Windows Firewall. |
| `ALREADY_ENFORCED` | La regla ya existía; no se duplica. |
| `SIMULATED_LOOPBACK` | Objetivo `127.0.0.1`/`::1`: se registra pero no se bloquea, para no cortar el HUD, FastAPI ni LM Studio. |
| `LOGICAL_BLOCK_ONLY` | Registrado solo en DuckDB (Uvicorn sin Administrador o sin `netsh`). |

En el HUD el botón muestra el estado real: **FIREWALL ACTIVO**, **SIMULADO (LOOPBACK)** o **SOLO LÓGICO (SIN ADMIN)**.

## 4. Flujo de trabajo de extremo a extremo

### Fase 1 — Arranque

Abre PowerShell **como Administrador**:

```powershell
Set-Location E:\vertex-forensic-lab
powershell -ExecutionPolicy Bypass -File .\Start-VertexLab.ps1
```

Comprueba en la salida:

- `Privilegios de Administrador : ACTIVOS`
- `Red WSL (NAT) : 172.x.x.x/20`
- `Regla VERTEX_LAB_INGRESS_8000 : TCP 8000 permitido SOLO desde ...`

### Fase 2 — Tráfico hostil

**Desde Windows (loopback, pruebas rápidas):**

```powershell
# Escáner clásico
curl.exe -s "http://localhost:8000/api/v2/internal/vault?node_id=1" -H "User-Agent: Mozilla/5.0 (Nikto/2.1.6)" -H "X-Swarm-Node: scanner-alpha"

# Enjambre: el Scout roba el Canary y el Exploit lo usa con SQLi
$resp = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/system/config" -Headers @{"User-Agent"="LangChain-Autonomous-Agent/1.0"; "X-Swarm-Node"="scout-node-01"}
$canary = $resp.debug_token_hint
curl.exe -s "http://localhost:8000/api/v2/internal/vault?node_id=1'%20UNION%20SELECT%20key_hash%20FROM%20vault--" -H "User-Agent: AutoGPT-Exploit-Worker/2.4" -H "Authorization: Bearer $canary"
```

**Desde Parrot (red real, IP 172.x):**

```bash
# Desde cualquier directorio dentro de Parrot
tr -d '\r' < /mnt/e/vertex-forensic-lab/tmp/swarm_assault.sh > /tmp/swarm_assault.sh
bash /tmp/swarm_assault.sh
```

El script ejecuta cuatro fases: escáner Nikto, Scout que roba el Canary, Exploit polimórfico con el token y un intento de abusar de la superficie de mando, que debe devolver `403`.

### Fase 3 — Peritaje

En el HUD pulsa **⚡ EJECUTAR PERITO LLM**. Cada sesión nueva recibe `AUTONOMOUS_AI_AGENT` o `LEGACY_SCANNER`, junto con su certeza, los indicadores que la justifican y el origen del dictamen (`LLM` o `DETERMINISTA`).

### Fase 4 — Contención

1. Localiza la tarjeta roja del Exploit de Parrot (IP `172.x.x.x`).
2. Pulsa **🔥 AISLAR HOST**. Con Administrador, el botón cambia a **🛡️ FIREWALL ACTIVO**.
3. Vuelve a lanzar `bash /tmp/swarm_assault.sh` en Parrot: la comprobación previa fallará por timeout. Eso confirma que el bloqueo funciona.

### Fase 5 — Acta y limpieza

- **📄 EXPORTAR ACTA SHA-256** genera `reports/ACTA_FORENSE_VERTEX_<fecha>.md` y su `.sha256`.
- Para retirar los bloqueos y repetir la prueba (PowerShell como Administrador):

```powershell
Set-Location E:\vertex-forensic-lab
powershell -ExecutionPolicy Bypass -File .\Stop-VertexLab.ps1 -RemoveBlocks
```

## 5. Integración MCP

Configura `vertex-forensic-mcp/server.py` en tu cliente MCP (transporte stdio). Herramientas disponibles:

- `get_recent_forensic_events(limit)`
- `get_forensic_verdicts_summary()`
- `get_swarm_handoff_lineage()`
- `block_suspicious_ip(ip_address, session_fingerprint)`, que usa el mismo módulo SOAR que el HUD.

Prueba rápida:

```powershell
Set-Location E:\vertex-forensic-lab\vertex-forensic-mcp
python client_test.py
```

La última prueba envía `1.2.3.4; whoami`, que debe rechazarse con un error de validación.

## 6. Despliegue en Docker (opcional)

```powershell
Set-Location E:\vertex-forensic-lab
docker compose up -d --build                  # honeypot
docker compose --profile attack up agent-simulator   # emulador de enjambre
```

La red usa `10.88.0.0/24` para no chocar con la red NAT de WSL. En Docker no hay `netsh`: los bloqueos quedan como `LOGICAL_BLOCK_ONLY`.

---

*Vertex Coders LLC — Miami, FL.*
