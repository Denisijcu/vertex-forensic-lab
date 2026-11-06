# VERTEX FORENSIC LAB — Observabilidad forense de enjambres IA y contención SOAR

**Vertex Forensic Lab (VFL) v1.3** es un laboratorio de defensa activa diseñado por **Vertex Coders LLC** (Miami, FL). Su propósito es detectar, perfilar, aislar y peritar el comportamiento de enjambres de agentes de IA autónomos (*multi-agent swarms*) y distinguirlos de los escáneres de vulnerabilidades tradicionales.

---

## Arquitectura

1. **Gateway de ingreso (FastAPI):** intercepta todo el tráfico HTTP con un middleware forense que calcula huella de sesión (SHA-256), entropía de Shannon y cadencia Δt.
2. **Capa de engaño:**
   - *Swarm Canary Tokens* firmados con HMAC-SHA256 (`vx_cnry_...`) en el endpoint trampa `/api/v1/system/config`, para rastrear el paso de credenciales entre nodos *Scout* y *Exploit*.
   - *Adaptive Tarpit*: retardos asíncronos crecientes que agotan el presupuesto de tiempo del atacante.
3. **Bóveda DuckDB:** `forensic_vault/telemetry.duckdb` (evidencia, linaje de enjambres, veredictos y acciones SOAR).
4. **Perito híbrido:** la clasificación la decide Python con indicadores duros; el modelo local `vertex-core-sec-turn` (LM Studio) solo redacta el dictamen y se descarta si contradice la evidencia.
5. **HUD táctico (Angular 19 + Tailwind):** supervisión en vivo, perito, aislamiento de hosts y actas firmadas.
6. **Servidor MCP (stdio):** consulta de la bóveda y bloqueo de IPs desde Claude Desktop, Cursor o LM Studio.

### Superficie de mando protegida (v1.3)

`/api/telemetry/*` y `/api/actions/*` solo responden a **loopback** (el HUD local). Cualquier otro origen recibe `403` y el intento queda registrado en la bóveda como `ADMIN_SURFACE_PROBE`, con tarpit incluido.

---

## Estructura

```text
vertex-forensic-lab/
├── backend/                  Gateway FastAPI, middleware forense, señuelos y SOAR
│   ├── lab_env.py            Configuración única (.env, DB_PATH, umbrales, política de mando)
│   ├── soar.py               Bloqueo netsh compartido por el backend y el MCP
│   ├── swarm_canary.py       Emisión y verificación de Canary Tokens
│   ├── adaptive_tarpit.py    Tarpit adaptativo
│   └── telemetry_api.py      API de telemetría para el HUD
├── frontend/                 HUD táctico en Angular 19
├── vertex-forensic-mcp/      Servidor MCP (server.py) y cliente de prueba
├── simulator/                Emulador de enjambre (perfil Docker "attack")
├── tmp/swarm_assault.sh      Asalto multivector desde Parrot (WSL2)
├── forensic_vault/           Bóveda DuckDB (no se versiona)
├── reports/                  Actas forenses firmadas (no se versionan)
├── forensic_coroner_llm.py   Perito híbrido
├── Start-VertexLab.ps1       Arranque (genera .env y regla de entrada WSL)
├── Stop-VertexLab.ps1        Parada (-RemoveBlocks, -RemoveIngress)
├── Invoke-VertexRelease.ps1  Empaquetado y sello SHA-256
├── Guia_de_Operacion.md      Manual de operación
└── OPERATIONS_QUICKREF.md    Referencia rápida de mando
```

---

## Inicio rápido

Desde PowerShell (como **Administrador** si quieres que el SOAR escriba reglas reales en Windows Firewall):

```powershell
Set-Location E:\vertex-forensic-lab
powershell -ExecutionPolicy Bypass -File .\Start-VertexLab.ps1
```

El script crea `.env` con un secreto aleatorio la primera vez, levanta FastAPI en `0.0.0.0:8000` y Angular en `4200`, y abre `http://localhost:4200`.

Para el manual completo (simulación de tráfico, perito, contención y MCP), consulta **[Guia_de_Operacion.md](Guia_de_Operacion.md)**.

---

## Requisitos

- Windows 11, PowerShell 5.1+.
- Python 3.10+ con `fastapi`, `uvicorn`, `duckdb`, `pydantic`, `httpx` (backend) y `mcp` (servidor MCP).
- Node.js 20+ y Angular CLI 19.
- LM Studio en `http://localhost:1234` con `vertex-core-sec-turn` (opcional: sin él, el perito emite dictámenes deterministas).

---

*Vertex Coders LLC — Miami, FL.*
