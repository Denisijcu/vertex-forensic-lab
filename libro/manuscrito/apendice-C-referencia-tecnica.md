# Apéndice C — Referencia técnica

## Tablas de la bóveda (`forensic_vault/telemetry.duckdb`)

### `forensic_evidence` — una fila por petición

| Columna | Tipo | Contenido |
|---|---|---|
| `event_id` | VARCHAR (PK) | Identificador `evt_…` |
| `timestamp` | DOUBLE | Instante Unix |
| `client_ip` | VARCHAR | IP de origen |
| `session_fingerprint` | VARCHAR | Huella de sesión (16 hex) |
| `http_method` | VARCHAR | Método HTTP |
| `endpoint` | VARCHAR | Ruta pedida |
| `query_params` | VARCHAR | Parámetros de consulta |
| `user_agent` | VARCHAR | User-Agent |
| `delta_t_ms` | DOUBLE | Tiempo desde la petición anterior de la misma huella |
| `payload_entropy` | DOUBLE | Entropía de Shannon de ruta, consulta y autorización |
| `tarpit_delay_ms` | DOUBLE | Retraso aplicado por el tarpit |
| `deception_triggered` | VARCHAR | Etiquetas de engaño |

### `swarm_lineage` — una fila por uso de un Canary Token

| Columna | Tipo | Contenido |
|---|---|---|
| `handoff_id` | VARCHAR (PK) | Identificador `swm_…` |
| `detected_at` | DOUBLE | Instante Unix del uso |
| `handoff_type` | VARCHAR | `LATERAL_SWARM_HANDOFF` o `SINGLE_AGENT_REPLAY` |
| `scout_fp` / `scout_ip` | VARCHAR | Huella e IP de quien recibió el token |
| `exploit_fp` / `exploit_ip` | VARCHAR | Huella e IP de quien lo presentó |
| `token_transit_ms` | DOUBLE | Tiempo entre la emisión y el uso |
| `endpoint_targeted` | VARCHAR | Ruta atacada con el token |

### `forensic_verdicts` — una fila por sesión peritada

| Columna | Tipo | Contenido |
|---|---|---|
| `session_fingerprint` | VARCHAR (PK) | Huella |
| `classification` | VARCHAR | `AUTONOMOUS_AI_AGENT` o `LEGACY_SCANNER` |
| `confidence` | DOUBLE | 0.95 o 0.90 |
| `deception_triggered` | BOOLEAN | Si hubo indicadores de agente |
| `verdict_json` | VARCHAR | Dictamen, origen, comentario del modelo, indicadores, contexto y cadencia |
| `evaluated_at` | DOUBLE | Instante Unix del peritaje |

Campos de `verdict_json`: `classification`, `confidence`, `reasoning` (dictamen oficial),
`reasoning_source` (`DETERMINISTA`), `llm_commentary` (comentario no vinculante o `null`), `indicators`,
`context` y `cadence_median_ms`.

### `soar_actions` — una fila por sesión contenida

| Columna | Tipo | Contenido |
|---|---|---|
| `session_fingerprint` | VARCHAR (PK) | Huella |
| `ip_address` | VARCHAR | IP bloqueada |
| `rule_name` | VARCHAR | Nombre de la regla de firewall |
| `enforcement_status` | VARCHAR | Estado SOAR |
| `reason` | VARCHAR | Motivo (`AUTONOMOUS_AI_AGENT_CONTAINMENT`, `MCP_AGENT_CONTAINMENT`) |
| `applied_at` | DOUBLE | Instante Unix |

## Estados SOAR

| Estado | Significado | Etiqueta en el panel |
|---|---|---|
| `ENFORCED_NETSH` | Regla creada en Windows Firewall | FIREWALL ACTIVO |
| `ALREADY_ENFORCED` | La regla ya existía | FIREWALL ACTIVO |
| `SIMULATED_LOOPBACK` | Objetivo local: registrado, no bloqueado | SIMULADO (LOOPBACK) |
| `LOGICAL_BLOCK_ONLY` | Solo en la bóveda (sin Administrador o sin `netsh`) | SOLO LÓGICO (SIN ADMIN) |

## Etiquetas de engaño

| Etiqueta | Cuándo se pone | Peso en el tarpit |
|---|---|---|
| `STANDARD_PROBE` | Petición sin nada destacable | 0 |
| `LATERAL_SWARM_HANDOFF` | Canary Token válido presentado por otra huella | 3 |
| `SINGLE_AGENT_REPLAY` | Canary Token válido presentado por la misma huella | 3 |
| `TAMPERED_CANARY` | Canary Token con firma alterada | 3 |
| `SQLI_HIGH_ENTROPY` | Entropía ≥ umbral, comilla simple o `UNION` en la consulta | 2 |
| `ADMIN_SURFACE_PROBE` | Petición a la superficie de mando desde fuera de loopback | 2 |

## Indicadores del perito

**Deciden la clasificación** (uno basta para `AUTONOMOUS_AI_AGENT`): transferencia lateral en
`swarm_lineage`, Canary Token emitido a otra huella, Canary Token alterado, entropía máxima ≥ 4.5 bits,
cadencia mediana ≥ 1000 ms y User-Agent con LangChain, LangGraph, AutoGPT, CrewAI, Agent o Swarm.

**Solo contexto:** acceso a la trampa, cargas de inyección SQL e intentos sobre la superficie de mando.

## Curva del tarpit

Retraso = `min(0.35 × 1.75^(puntaje − 1), 6.0)` segundos, sin retraso con puntaje ≤ 1.

## Variables de entorno

| Variable | Por defecto | Uso |
|---|---|---|
| `DB_PATH` | `forensic_vault/telemetry.duckdb` | Ruta de la bóveda |
| `VERTEX_CANARY_SECRET` | efímero | Secreto HMAC de los Canary Tokens |
| `VERTEX_ENTROPY_THRESHOLD` | `4.5` | Umbral de entropía en bits |
| `VERTEX_ADMIN_ALLOWED_CIDRS` | vacío | Redes extra con acceso a la superficie de mando |
| `VERTEX_HUD_ORIGINS` | `http://localhost:4200,http://127.0.0.1:4200` | Orígenes CORS del panel |
| `LM_STUDIO_URL` | `http://localhost:1234/v1/chat/completions` | API del modelo local |
| `MODEL_NAME` | `vertex-core-sec-turn` | Modelo del perito |
