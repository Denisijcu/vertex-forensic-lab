# Bitácora de Proyecto: Vertex Forensic Lab (Vertex Coders)

Laboratorio de observabilidad forense y contención SOAR contra enjambres de agentes de IA: gateway FastAPI con señuelos (Canary Tokens HMAC y tarpit adaptativo), bóveda DuckDB, perito híbrido con un modelo local en LM Studio, HUD en Angular 19 y servidor MCP.

---

## [2026-11-02 / 2026-11-03] — Antecedentes (según los archivos del proyecto)
- **Release v1.0:** `C:\VertexBackups\Vertex-Forensic-Lab_v1.0_20261102_212233.zip`, SHA-256 `DAF2F8FC24AC59D378193B2A0D1329A7964C7F99836B5106720CE42DB473268A` (anotado en `Informe-Tecnico.md`).
- **Autopsias:** `forensic_vault/reports/autopsy_report_20261102_130622.md` y `..._130716.md`.
- **Actas v1.2:** cuatro en `reports/`, emitidas el 2026-11-03 entre las 07:05 y las 07:09 UTC, con su `.sha256`.
- **Pruebas hasta ese momento:** todas por loopback (`127.0.0.1`), así que todos los bloqueos quedaron `SIMULATED_LOOPBACK`. Tres sesiones de referencia: Nikto (`14eda62f…`), Scout LangChain (`8e5079bb…`) y Exploit AutoGPT (`54ab92fd…`), con 3 handoffs de canary (360, 2458 y 7420 ms).

## [2026-11-06 14:34 EST] — Revisión inicial del proyecto
- **Estado encontrado:** gateway, señuelos, bóveda, perito, HUD, MCP y scripts PowerShell funcionando en loopback. Documentación en versiones mezcladas: el informe decía v1.1, las actas v1.2 y el zip v1.0.
- **Hallazgos:**
  1. **`/api/telemetry` y `/api/actions` sin autenticación, con CORS `*`.** Con uvicorn como Admin en `0.0.0.0` y la regla de entrada abierta a cualquier IP, alguien en la red podía disparar `firewall-block` y bloquear IPs legítimas, y ese abuso no se registraba.
  2. **Ruta de la bóveda en Docker:** `main.py` ignoraba `DB_PATH` (resolvía a `/forensic_vault` con el sistema de archivos en solo lectura).
  3. **MCP:** `block_suspicious_ip` ejecutaba `CREATE` + `INSERT` con parámetros en un solo `execute`.
  4. **Secreto del canary** escrito en `docker-compose.yml` y como valor por defecto en el código.
  5. **Umbral de entropía:** 4.2 bits en el código y 4.5 en el informe.
  6. **El perito LLM alucinaba:** llamaba "alta" a 3.914 bits y razonaba en inglés.
  7. **Documentación** con respuestas de chat pegadas, bloques de código rotos y referencia a una `Guia_de_Operacion.md` que no existía.
- **Estado de la máquina:** WSL2 en modo NAT; `vEthernet (WSL)` = `172.28.48.1/20`; LM Studio activo en `:1234`; puertos 8000 y 4200 libres; sin reglas `VERTEX_LAB_*` ni `VERTEX_BLOCK_*`.

## [2026-11-06 14:42–14:56 EST] — v1.3: hardening y corrección de bugs
- **Superficie de mando solo loopback**, con doble control (middleware y dependencia de FastAPI). Un origen remoto recibe 403, suma peso en el tarpit y queda en la bóveda como `ADMIN_SURFACE_PROBE`. CORS limitado a `localhost:4200`.
- **Nuevos módulos:** `backend/lab_env.py` (carga `.env`, `DB_PATH`, umbrales y política de mando) y `backend/soar.py` (bloqueo netsh único para el backend y el MCP). `soar.py` valida la IP, rechaza 0.0.0.0, multicast y broadcast, no duplica reglas (`ALREADY_ENFORCED`) y cubre la falta de netsh (`LOGICAL_BLOCK_ONLY`).
- **Bugs corregidos:**
  - Un canary con la firma alterada tumbaba el middleware con un `KeyError` (HTTP 500). Ahora se etiqueta `TAMPERED_CANARY`.
  - **Conflicto de red:** el compose usaba `172.28.0.0/16`, que contiene la red de WSL (`172.28.48.0/20`). Pasa a `10.88.0.0/24`.
  - El simulador leía `TARGET_HOST`, pero el compose le pasaba `TARGET_URL`.
  - `forensic_report_compiler.py` consultaba columnas inexistentes (`verdict_id`, `analyzed_at`) y generaba `netsh` contra `127.0.0.1`.
  - `autopsy.py` e `inspect_verdicts.py` solo funcionaban desde la raíz (rutas relativas).
- **Secretos:** `Start-VertexLab.ps1` genera `.env` con `VERTEX_CANARY_SECRET` aleatorio. Queda excluido de git y del release.
- **Regla de entrada** `VERTEX_LAB_INGRESS_8000`, solo desde la subred NAT de WSL, recalculada en cada arranque. `Stop-VertexLab.ps1` gana `-RemoveBlocks` y `-RemoveIngress`.
- **HUD:** el botón muestra el estado real (FIREWALL ACTIVO / SIMULADO / SOLO LÓGICO) y el detalle de los errores del backend.
- **Script de ataque** `tmp/swarm_assault.sh` con 4 fases. La nueva es el abuso de la superficie de mando, y debe dar 403.
- **Documentación reescrita:** README, `Guia_de_Operacion.md` (nueva), `OPERATIONS_QUICKREF.md`, Informe v1.3 y README del backend y del simulador.
- **Incidente de herramientas:** la llamada a PowerShell que incluía `wsl -d Parrot` se colgó, y el servidor dejó de responder durante la sesión. No se pudo ejecutar `py_compile` desde aquí; la validación quedó en manos de Denis.

## [2026-11-06 14:56 EST] — Prueba 1 desde Parrot: el tráfico cruza la red real
- **Las sesiones de Parrot llegan con la IP `172.28.56.172`**, contra el objetivo `172.28.48.1:8000`. Ya no pasan por loopback.
- **Sesiones capturadas:** Nikto `d7820db7…` (3 peticiones, 3.992 bits), Scout `520cc6f8…` (robó el canary) y Exploit `a9101753…` (5.692 bits, 3 handoffs con tránsitos de 1825, 6905 y 14688 ms).
- **El HUD mostraba 2 peticiones del Exploit con 3 handoffs.** Es un desfase esperado: el handoff se registra al llegar la petición y la evidencia se escribe cuando el tarpit suelta el socket.

## [2026-11-06 15:00 EST] — Prueba 2: script viejo y tarpit en el tope
- **Se ejecutó por error el `/tmp/swarm_assault.sh` de la guía anterior**, de 3 fases, porque faltó el paso del `tr`.
- **Tarpit:** ~6.4 s en los tres impactos, cuando se esperaban 3.3 → 6 → 6 s. **Causa:** el puntaje de sospecha vive en memoria por huella y nunca baja mientras el gateway corre. La huella del Exploit (IP + User-Agent + nodo) ya venía de la corrida anterior y arrancó en el tope de 6 s.
- **Costo de E/S:** los ~0.4 s por encima del tope, y los ~0.2 s de cada sondeo de Nikto, salen de abrir y cerrar DuckDB en cada petición.

## [2026-11-06 15:03 EST] — Prueba 3: script v1.3 completo
- **Fase 1 (Nikto):** HTTP 500 en ~0.2 s, sin tarpit.
- **Fase 2 (Scout):** canary exfiltrado.
- **Fase 3 (Exploit):** HTTP 200 `PARTIAL_DUMP` en 6.388, 6.377 y 6.390 s.
- **Fase 4:** `GET /api/telemetry/state` y `POST /api/actions/firewall-block` desde Parrot → **HTTP 403** en los dos.

## [2026-11-06 15:06 EST] — Primer peritaje: tres fallos del perito
- **Falso positivo:** Nikto `d7820db7…` salió `AUTONOMOUS_AI_AGENT`. **Causa:** el perito usaba el Δt **medio** de toda la sesión, y con 9 peticiones repartidas en tres corridas, los minutos entre corridas lo inflaron a 46 381 ms y cruzó el umbral de cadencia (1000 ms).
- **Falso positivo:** `cd6aef31…` (1 petición, un `curl` pelado) salió `AUTONOMOUS_AI_AGENT`. **Causa:** la comprobación previa del script tocaba el endpoint trampa, y "tocar la trampa" contaba como indicador de agente. Un escáner clásico también la toca.
- **LM Studio:** HTTP 400 en las dos primeras sesiones y respuestas correctas en las siguientes. La causa probable era que el modelo todavía estaba cargando (JIT).
- **Correcciones** (`forensic_coroner_llm.py`):
  - La cadencia pasa a ser la **mediana del Δt dentro de ráfagas** (se descartan pausas de más de 30 s).
  - Indicadores de agente (deciden la clasificación): handoff entre huellas distintas, canary ajeno o alterado, entropía ≥ 4.5 bits, cadencia ≥ 1000 ms y User-Agent agéntico.
  - Solo contexto (no deciden): tocar la trampa, enviar SQLi y sondear la superficie de mando.
  - 3 reintentos contra LM Studio, con el cuerpo del error en el log.
  - Re-evaluación automática de las sesiones con actividad posterior a su veredicto, más la opción `--rejudge`.
- **Script de ataque:** la comprobación previa va a `/` con su propia huella (`Vertex-Precheck/1.3`).

## [2026-11-06 15:13–15:17 EST] — Peritaje corregido, aislamiento y prueba de fuego
- **Perito (re-evaluación automática), 4 sesiones, 0 errores de LM Studio:** Scout y Exploit → `AUTONOMOUS_AI_AGENT` (95%); Nikto `d7820db7…` y la comprobación previa `e0a84ad3…` → `LEGACY_SCANNER` (90%). `cd6aef31…` también quedó `LEGACY_SCANNER`.
- **Aislamiento del Exploit desde el HUD:** `ENFORCED_NETSH`, con la regla `VERTEX_BLOCK_a9101753_172.28.56.172` escrita en Windows Firewall.
- **Prueba de fuego:** al repetir `bash /tmp/swarm_assault.sh`, la comprobación previa falló por timeout. **Parrot quedó fuera de la red del host.**

## [2026-11-06 15:18 EST] — Ajustes del HUD
- **Bloqueo por IP:** una regla real en netsh (`ENFORCED_NETSH` o `ALREADY_ENFORCED`) cubre todas las sesiones de esa IP, en el HUD y en el acta. Los bloqueos simulados de loopback no se propagan.
- **Consulta única** `backend/session_queries.py`, que comparten el HUD y el acta. Muestra la **cadencia mediana** igual que el perito, en lugar del Δt medio. Los umbrales de cadencia quedan en `lab_env.py`.

## [2026-11-06 15:22 EST] — Acta 1: el LLM no puede dar fe
- **Acta** `ACTA_FORENSE_VERTEX_20261106_152157.md` (SHA-256 del archivo `DAFFEFA1ED8D26CE…`). Los datos estaban correctos: 9 sesiones, 15 handoffs y el bloqueo propagado a las 5 sesiones de Parrot.
- **Dictámenes redactados por el LLM: 7 de 9 contradecían la evidencia.**
  - Afirmaba que 3.914 y 3.992 bits "superaban" el umbral de 4.5.
  - Atribuía "malware" o "agente malicioso" a escáneres.
  - Repetía la instrucción del prompt ("No calificamos como 'alta'…").
- **El validador anterior no los atrapó:** solo buscaba la frase literal "alta entrop".
- **Decisión de diseño:** el dictamen **oficial** del acta es siempre el determinista, construido con los indicadores reales. El texto del LLM se guarda como `llm_commentary` (no vinculante), solo si pasa un validador frase a frase que revisa las cifras de entropía, rechaza el eco del prompt y prohíbe atribuir intención maliciosa a un `LEGACY_SCANNER`.

## [2026-11-06 15:25 EST] — Acta final y cierre técnico
- **Acta** `ACTA_FORENSE_VERTEX_20261106_152518.md`, sello del cuerpo `E1773E9F167D9AE81FB3A54E87B81F726439FFED61CB71E02908662E33A2ADCF`. Las 9 sesiones salen con el veredicto correcto y con dictámenes coherentes con los datos.

| Sesión | Origen | Peticiones | Cadencia mediana | Entropía máx. | Veredicto | Contención |
|---|---|---|---|---|---|---|
| `a9101753…` Exploit AutoGPT/LangGraph | 172.28.56.172 | 16 | 7791.45 ms | 5.716 bits | AUTONOMOUS_AI_AGENT 95% | ENFORCED_NETSH |
| `520cc6f8…` Scout CrewAI | 172.28.56.172 | 4 | 0.0 ms | 3.914 bits | AUTONOMOUS_AI_AGENT 95% | ENFORCED_NETSH (por IP) |
| `d7820db7…` Nikto | 172.28.56.172 | 12 | 223.5 ms | 3.992 bits | LEGACY_SCANNER 90% | ENFORCED_NETSH (por IP) |
| `e0a84ad3…` Precheck | 172.28.56.172 | 1 | 0.0 ms | 1.0 bits | LEGACY_SCANNER 90% | ENFORCED_NETSH (por IP) |
| `cd6aef31…` curl | 172.28.56.172 | 1 | 0.0 ms | 3.914 bits | LEGACY_SCANNER 90% | ENFORCED_NETSH (por IP) |
| 4 sesiones de las pruebas del 03-nov | 127.0.0.1 | — | — | — | 3 AUTONOMOUS_AI_AGENT, 1 LEGACY_SCANNER (Nikto) | SIMULATED_LOOPBACK |

- **Linaje:** 15 handoffs `LATERAL_SWARM_HANDOFF`; 12 de ellos Scout `520cc6f8` → Exploit `a9101753`, con tránsitos de 1812 a 17487 ms.
- **Ciclo validado de punta a punta con tráfico real:** detección → linaje canary → tarpit → perito → bloqueo netsh → atacante fuera → acta firmada.

## [2026-11-06 15:30–16:30 EST] — Cierre: video promo y libro
- **Video promo:** `F:\vertex-videos\forensic_lab.py`, escena `VertexForensicPromo`, 8 tomas y ~90 s, con cifras de esta bitácora y del acta final. Denis lo renderizó y lo aprobó ("así se queda").
- **Libro *Vertex Forensic Lab*:** plan en `libro/PLAN.md`; manuscrito completo en `libro/manuscrito/` (5 preliminares, 12 capítulos, conclusión, 3 apéndices y "Sobre el autor").
- **Build:** `libro/build_pdf.py` (6x9, el mismo diseño de la serie, con conversión de `Δ`, `→`, `≥` y `≈` en la prosa porque la serif no los tiene), `libro/build_epub.py`, `libro/portada/build_art.py` y `build_cover.py` (con `PAGES = 160` provisional) y `libro/kdp-ficha.md`. Fuentes copiadas de `vertex-text2sql-engine/libro/fonts`.
- **Pendiente de Denis:** compilar el PDF, el EPUB y la portada, y ajustar `PAGES` con el número real de páginas. Revisión conjunta del manuscrito y aprobación.
- **Hallazgo al escribir el capítulo 11:** las herramientas MCP devuelven al modelo evidencias escritas en parte por el atacante (rutas, User-Agent). Riesgo de inyección indirecta de instrucciones; se añade a los pendientes.

## Pendientes para una v1.4
- Etiquetar como `CANARY_MINTED` la petición del Scout a la trampa (hoy sale `STANDARD_PROBE`).
- Fusionar los indicadores "transferencia lateral" y "token emitido a otra huella", que se solapan.
- Decaimiento del puntaje del tarpit en el tiempo. Hoy no baja mientras el gateway corre.
- Una sola conexión DuckDB por proceso, para quitar los ~0.2 s por petición.
- Neutralizar en las herramientas MCP el contenido escrito por el cliente remoto (riesgo de inyección indirecta), y mantener siempre la confirmación humana en `block_suspicious_ip`.
- Firma digital o sello de tiempo para el acta (hoy el SHA-256 prueba integridad, no autoría).
- Probar el despliegue Docker. Falta confirmar qué IP de origen ve el contenedor desde el HUD del host (`VERTEX_ADMIN_ALLOWED_CIDRS=10.88.0.1/32`).
- **Orden de cierre:** video promo (Manim) → libro.
