# Vertex Forensic Backend — Honeypot y motor de engaño

Subsistema en **FastAPI** y **DuckDB** que actúa como sensor forense, trampa de contención y emisor de canarios criptográficos.

## Módulos

| Archivo | Responsabilidad |
| --- | --- |
| `lab_env.py` | Carga `.env`, fija `DB_PATH`, el umbral de entropía y la política de mando (solo loopback). Se importa primero. |
| `main.py` | Gateway: middleware forense, endpoints señuelo (`/api/v1/system/config`, `/api/v2/internal/vault`) y acciones SOAR. |
| `telemetry_api.py` | API de solo lectura para el HUD (`/api/telemetry/state`), protegida a loopback. |
| `soar.py` | Bloqueo en Windows Firewall con `netsh`, compartido con el servidor MCP. |
| `swarm_canary.py` | Emisión y verificación de Canary Tokens HMAC-SHA256. |
| `adaptive_tarpit.py` | Retardo exponencial por huella de sesión (tope de 6 s). |

## Variables de entorno

| Variable | Por defecto | Uso |
| --- | --- | --- |
| `DB_PATH` | `forensic_vault/telemetry.duckdb` | Ruta de la bóveda (en Docker: `/app/vault/telemetry.duckdb`). |
| `VERTEX_CANARY_SECRET` | efímero | Secreto HMAC de los Canary Tokens. |
| `VERTEX_ENTROPY_THRESHOLD` | `4.5` | Umbral de entropía (bits) para la etiqueta `SQLI_HIGH_ENTROPY`. |
| `VERTEX_ADMIN_ALLOWED_CIDRS` | vacío | Redes extra con acceso a la superficie de mando (Docker: gateway del bridge). |
| `VERTEX_HUD_ORIGINS` | `http://localhost:4200,http://127.0.0.1:4200` | Orígenes CORS del HUD. |

## Tablas DuckDB

1. `forensic_evidence`: telemetría por petición (entropía, Δt, tarpit, etiquetas).
2. `swarm_lineage`: transferencias de Canary Tokens (Scout → Exploit).
3. `forensic_verdicts`: dictámenes del perito híbrido.
4. `soar_actions`: reglas de contención aplicadas y su estado.

## Arranque manual

```powershell
Set-Location E:\vertex-forensic-lab\backend
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```
