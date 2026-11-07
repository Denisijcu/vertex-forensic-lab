# DOCUMENTO DE ARQUITECTURA E INGENIERÍA DE SEGURIDAD

**Proyecto:** Vertex Forensic Lab (VFL) — Observabilidad Forense de Enjambres IA y Contención Activa SOAR

**Organización:** Vertex Coders LLC (Miami, Florida)

**Autor / Arquitecto Principal:** Denis Sanchez Leyva

**Versión del Sistema:** `v1.3` (hardening de la superficie de mando, módulo SOAR unificado y perito híbrido revisado)

**Clasificación:** Especificación Técnica de Ingeniería Defensiva y DevSecOps

---

## 1. Resumen Ejecutivo

**Vertex Forensic Lab (VFL)** es una plataforma de contrainteligencia, engaño activo (*Active Deception*) y respuesta automatizada ante incidentes (*SOAR*) diseñada para detectar, perfilar y neutralizar ataques ejecutados por enjambres de agentes de inteligencia artificial autónomos (*Multi-Agent AI Swarms*).

A diferencia de los cortafuegos de aplicaciones web tradicionales (WAF) basados en firmas estáticas, VFL analiza la física del tráfico en tiempo real mediante tres vectores matemáticos y criptográficos:

1. **Entropía de Shannon ($H(X)$):** Cuantifica la densidad informacional y mutación polimórfica de cada petición HTTP.


2. **Cadencia Cognitiva ($\Delta t$):** Mide los intervalos de inferencia entre peticiones consecutivas para distinguir bucles mecánicos de procesos de razonamiento LLM.


3. **Trazabilidad de Linaje Criptográfico (*Swarm Lineage*):** Rastrea el robo e intercambio lateral de credenciales señuelo (*Canary Tokens*) entre nodos exploradores (*Scout*) y nodos ejecutores (*Exploit Worker*).

El ecosistema integra un gateway asíncrono en **FastAPI**, almacenamiento columnar inmutable en **DuckDB**, un motor de peritaje híbrido impulsado localmente por el modelo GGUF **`vertex-core-sec-turn`**, un centro de mando visual en **Angular 19** y un servidor **Model Context Protocol (MCP)** para orquestación agéntica.

---

## 2. Arquitectura del Sistema y Flujo de Datos

La arquitectura se divide en cinco capas desacopladas que operan con latencia sub-milisegundo en la captura y aislamiento determinista en la respuesta:

| Capa Arquitectónica | Tecnología Base | Responsabilidad Técnica Principal |
| --- | --- | --- |
| **1. Gateway & Middleware Forense** | Python / FastAPI | Intercepción HTTP, cálculo de huella SHA-256, entropía de Shannon y $\Delta t$. |
| **2. Deception & Tarpit Engine** | HMAC-SHA256 / AsyncIO | Emisión de Canary Tokens (`vx_cnry_`) e inyección de latencia adaptativa (*Tarpit*). |
| **3. Bóveda Forense Inmutable** | DuckDB (`telemetry.duckdb`) | Persistencia columnar ACID de evidencia cruda, linaje de enjambres y veredictos.

 |
| **4. Perito Cognitivo Híbrido** | GGUF (`vertex-core-sec-turn`) | Evaluación heurística pre-filtrada + redacción pericial bajo esquema JSON estricto.

 |
| **5. Interfaz SOAR & Servidor MCP** | Angular 19 / FastMCP / `netsh` | Visualización en tiempo real, disparo de peritajes y bloqueo en Windows Firewall.

 |

---

## 3. Fundamentación Matemática y Criptográfica

### 3.1. Identificación de Sesión sin Estado (*Stateless Fingerprinting*)

Para rastrear actores sin depender de cookies vulnerables a manipulación, el middleware genera un identificador único truncado de 64 bits (16 caracteres hexadecimales) por cada combinación de origen de red, agente de usuario e identificador de nodo de enjambre:

$$\text{FP} = \text{SHA256}\left(\text{IP}_{\text{client}} \parallel \text{"\vert{}"} \parallel \text{User-Agent} \parallel \text{"\vert{}"} \parallel \text{X-Swarm-Node}\right)_{}$$

### 3.2. Cálculo de Entropía de Shannon ($H(X)$)

Sobre la cadena concatenada de ruta, parámetros de consulta y cabecera de autorización ($S = \text{Path} \parallel \text{"?"} \parallel \text{Query} \parallel \text{Auth}$), se calcula la entropía de Shannon en bits por símbolo:

$$H(X) = -\sum_{i=1}^{n} P(x_i) \log_2 P(x_i), \quad \text{donde } P(x_i) = \frac{\text{frecuencia}(x_i)}{\vert{}S\vert{}}$$

* **Tráfico Estático / Escáner Legacy:** Presenta baja diversidad léxica ($H(X) \in [3.5, 4.1]\text{ bits}$).


* **Inyección Polimórfica / Canary Handoff:** La combinación de tokens criptográficos y cargas SQL mutadas eleva la entropía por encima del umbral crítico ($H(X) \ge 4.5\text{ bits}$, alcanzando $5.669\text{ bits}$ en pruebas de intrusión).



### 3.3. Cadencia Temporal ($\Delta t$) y Degradación por Tarpitting

El motor mantiene un diccionario en memoria caliente (`LAST_SEEN_TS`) para medir el tiempo transcurrido entre peticiones sucesivas de una misma huella:

$$\Delta t_k = \begin{cases} 0.0\text{ ms} & \text{si } k = 1 \\ (t_k - t_{k-1}) \times 1000 & \text{si } k > 1 \end{cases}$$

Cuando una sesión acumula pesos de anomalía ($w \ge 2$ por SQLi o $w \ge 3$ por uso de Canary Token), el **Adaptive Tarpit** retiene asíncronamente el socket antes de devolver respuesta, forzando un agotamiento en los *timeouts* y ventanas de ejecución del orquestador atacante.

### 3.4. Trazabilidad de Enjambres (*Swarm Canary Tokens*)

El endpoint trampa `/api/v1/system/config` emite tokens señuelo con el formato `vx_cnry_<payload_b64>.<firma_hmac>`. El payload codifica el fingerprint del nodo que descubrió el recurso ($\text{FP}_{\text{scout}}$), su IP y el *timestamp* de emisión ($t_{\text{mint}}$).

Cuando un nodo posterior presenta ese token en la cabecera `Authorization: Bearer`, el verificador comprueba la integridad HMAC y evalúa:

* Si $\text{FP}_{\text{actual}} \neq \text{FP}_{\text{scout}}$, se confirma matemáticamente una **Transferencia Lateral de Enjambre (`LATERAL_SWARM_HANDOFF`)** y se calcula el tiempo de tránsito cognitivo:

$$\Delta t_{\text{transit}} = (t_{\text{uso}} - t_{\text{mint}}) \times 1000\text{ ms}$$



---

## 4. Esquema de Datos en la Bóveda Inmutable (DuckDB)

La base de datos `forensic_vault/telemetry.duckdb` estructura la evidencia en tres tablas relacionales-columnares:

### 4.1. Tabla `forensic_evidence` (Telemetría Cruda por Petición)

* `event_id` (`VARCHAR PRIMARY KEY`): Identificador único de evento (`evt_...`).
* `timestamp` (`DOUBLE`): Tiempo Unix en alta precisión.
* `client_ip` (`VARCHAR`): Dirección IPv4/IPv6 de origen.
* `session_fingerprint` (`VARCHAR`): Hash SHA-256 truncado de la sesión.
* `http_method` / `endpoint` / `query_params` / `user_agent` (`VARCHAR`): Metadatos HTTP.
* `delta_t_ms` (`DOUBLE`): Intervalo en milisegundos respecto a la petición previa.


* `payload_entropy` (`DOUBLE`): Entropía de Shannon calculada en bits.


* `tarpit_delay_ms` (`DOUBLE`): Retardo defensivo inyectado a la petición.
* `deception_triggered` (`VARCHAR`): Etiquetas de alerta (`STANDARD_PROBE`, `LATERAL_SWARM_HANDOFF`, `SQLI_HIGH_ENTROPY`).

### 4.2. Tabla `swarm_lineage` (Cadena de Custodia de Movimiento Lateral)

* `handoff_id` (`VARCHAR PRIMARY KEY`): Identificador de transferencia (`swm_...`).
* `detected_at` (`DOUBLE`): Timestamp del impacto.
* `handoff_type` (`VARCHAR`): Clasificación de transferencia (`LATERAL_SWARM_HANDOFF`).
* `scout_fp` / `scout_ip` (`VARCHAR`): Huella e IP del agente explorador original.
* `exploit_fp` / `exploit_ip` (`VARCHAR`): Huella e IP del agente ejecutor que utilizó el token.
* `token_transit_ms` (`DOUBLE`): Tiempo transcurrido entre el robo del token y su explotación.
* `endpoint_targeted` (`VARCHAR`): Recurso atacado con la credencial señuelo.

### 4.3. Tabla `forensic_verdicts` (Dictámenes Periciales)

* `session_fingerprint` (`VARCHAR PRIMARY KEY`): Huella auditada.
* `classification` (`VARCHAR`): Veredicto (`AUTONOMOUS_AI_AGENT` o `LEGACY_SCANNER`).


* `confidence` (`DOUBLE`): Nivel de certeza estadística (`0.0` a `1.0`).


* `deception_triggered` (`BOOLEAN`): Indicador de compromiso en trampas activas.
* `verdict_json` (`VARCHAR`): Dictamen íntegro y razonamiento emitido por el LLM.
* `evaluated_at` (`DOUBLE`): Timestamp de la autopsia.

---

## 5. Motor de Peritaje Híbrido (Determinista + Cognitivo Local)

Para erradicar las alucinaciones en modelos locales compactos (2B–4B parámetros) y evitar fallos de parseo por caracteres de control en cadenas JSON, el módulo `forensic_coroner_llm.py` implementa un diseño de **Doble Escudo**:

1. **Pre-Evaluación Determinista (*Zero-Hallucination Guardrail*):**
Python cruza en una sola consulta SQL la tabla `forensic_evidence` con `swarm_lineage` para determinar si la sesión actuó como *Scout* o *Exploit* en una transferencia entre huellas distintas, si superó el umbral de entropía ($H(X) \ge 4.5\text{ bits}$) o de cadencia, o si declaró firmas de frameworks agénticos (`LangChain`, `LangGraph`, `AutoGPT`, `CrewAI`). La cadencia se mide como la **mediana de $\Delta t$ dentro de ráfagas** (se descartan pausas mayores de 30 s), porque la media se infla con los silencios entre corridas y llevó a clasificar un escáner como agente en las pruebas v1.3. Tocar la trampa, enviar SQLi o sondear la superficie de mando se registran como **contexto** y no deciden la clasificación: un escáner clásico también lo hace. Las sesiones con actividad posterior a su último veredicto se re-evalúan automáticamente.
2.  Inferencia Estructurada con Gramática Forzada (`json_schema`):
Se invoca a `vertex-core-sec-turn` en LM Studio (`http://localhost:1234/v1/chat/completions`) con un esquema JSON estricto que solo pide el campo `reasoning`: la clasificación y la certeza nunca salen del modelo. El prompt le entrega la lista de indicadores ya confirmados y los umbrales, con la orden de no inventar otros.
3. **Dictamen Oficial Determinista (v1.3):** En las pruebas con tráfico real desde Parrot, el modelo compacto redactó dictámenes que contradecían la evidencia en 7 de 9 sesiones: afirmó que entropías de 3.9 bits "superaban" el umbral de 4.5, atribuyó malware a un escáner o repitió las instrucciones del prompt. Por eso el texto que entra en el acta firmada es **siempre** el dictamen determinista, construido con los indicadores reales. La redacción del LLM se conserva como `llm_commentary` (no vinculante) solo si supera un validador que revisa frase a frase las cifras de entropía, rechaza el eco del prompt y prohíbe atribuir intención maliciosa a un `LEGACY_SCANNER`. Lección de diseño: en un documento con cadena de custodia, el modelo puede asistir, pero no puede dar fe.



---

## 6. Hardening DevSecOps y Contención SOAR

El módulo de respuesta activa implementa controles estrictos de seguridad ofensiva/defensiva:

* **Prevención de Inyección de Comandos (RCE Mitigation):** El endpoint `/api/actions/firewall-block` y la herramienta MCP `block_suspicious_ip` validan la dirección IP entrante mediante el parser nativo `ipaddress.ip_address()` antes de pasar cualquier argumento al subproceso del sistema operativo (`netsh advfirewall`). Cualquier cadena malformada o intento de concatenación de comandos (`;`, `&`, `|`) es rechazado inmediatamente con código HTTP `400`.
* **Salvaguarda de Loopback (`127.0.0.1` / `::1`):** Durante simulaciones locales, el sistema intercepta las órdenes de bloqueo dirigidas a la interfaz local y registra una regla simulada (`simulated_loopback`), evitando que el operador corte accidentalmente la comunicación entre Angular, FastAPI y LM Studio.


* **Superficie de Mando Restringida a Loopback (v1.3):** Los prefijos `/api/telemetry` y `/api/actions` solo responden a `127.0.0.1`/`::1` (el HUD local), con doble control: middleware y dependencia de FastAPI. Cualquier otro origen recibe `403`, acumula peso en el tarpit y queda registrado en la bóveda con la etiqueta `ADMIN_SURFACE_PROBE`. Así un atacante en la red no puede usar el SOAR para bloquear IPs legítimas (gateway, DNS).
* **Aislamiento de Telemetría del Propio HUD:** Las consultas del HUD local no se registran como evidencia, para que el refresco del navegador y los clics del operador no contaminen la bóveda.
* **Reglas sin Duplicados:** Antes de crear una regla, `netsh` comprueba si ya existe (`ALREADY_ENFORCED`). Backend y MCP comparten un único módulo (`backend/soar.py`).
* **Gestión de Secretos:** `VERTEX_CANARY_SECRET` vive en `.env` (excluido de git y del release), generado aleatoriamente por `Start-VertexLab.ps1`. Sin secreto configurado, el gateway usa uno efímero por proceso.
* **Ingreso Acotado:** La regla `VERTEX_LAB_INGRESS_8000` permite el puerto 8000 solo desde la subred NAT de WSL, calculada en cada arranque.

---

## 7. Integración con el Ecosistema Model Context Protocol (MCP)

El servidor `vertex-forensic-mcp/server.py` expone la infraestructura forense a través del protocolo estándar **MCP** sobre transporte `stdio`, dotando a cualquier agente autorizado de cuatro herramientas tácticas:

* `get_recent_forensic_events(limit)`: Inspección en vivo de los últimos paquetes interceptados.
* `get_forensic_verdicts_summary()`: Consulta de sesiones clasificadas y nivel de certeza pericial.
* `get_swarm_handoff_lineage()`: Reconstrucción completa de la cadena de ataque *Scout* $\rightarrow$ *Exploit*.
* `block_suspicious_ip(ip_address, session_fingerprint)`: Ejecución remota de reglas de denegación en Windows Defender Firewall.

---

## 8. Resultados de Validación Experimental (Auditoría de Laboratorio)

Durante la batería de pruebas de extremo a extremo realizada sobre la versión `v1.1`, el sistema clasificó correctamente las tres sesiones de prueba. Es una validación funcional sobre tráfico sintético controlado, no una medida estadística de precisión; la evaluación con tráfico real queda como trabajo futuro:

| Huella de Sesión (`FP`) | Actor / User-Agent | Endpoint Objetivo | $\Delta t$ Medio | Entropía Máx. | Rol Detectado en Enjambre | Veredicto Final (Certeza) |
| --- | --- | --- | --- | --- | --- | --- |
| `14eda62fb70f5166` | `Mozilla/5.0 (Nikto/2.1.6)` | `/api/v2/internal/vault` | `0.0 ms` | `3.992 bits` | Ninguno (`STANDARD_PROBE`) | `LEGACY_SCANNER` (`90.0%`)

 |
| `8e5079bbc8543059` | `LangChain-Autonomous-Agent/1.0` | `/api/v1/system/config` | `0.0 ms` | `3.914 bits` | **Nodo Scout** (Extrae Canary) | `AUTONOMOUS_AI_AGENT` (`95.0%`)

 |
| `54ab92fd4d95069b` | `AutoGPT-Exploit-Worker/2.4` | `/api/v2/internal/vault` | `2481.16 ms` | `5.669 bits` | **Nodo Exploit** (Handoff + SQLi) | `AUTONOMOUS_AI_AGENT` (`95.0%`)

 |

* **Evidencia de Tránsito Lateral:** La tabla `swarm_lineage` registró dos impactos del token robado por `8e5079bbc8543059` y ejecutado por `54ab92fd4d95069b`: el primero a los `2458.0 ms` y el segundo a los `7420.0 ms` (demostrando la retención efectiva del *Adaptive Tarpit*).
* **Integridad de Release (histórico):** El paquete maestro `Vertex-Forensic-Lab_v1.0_20261102_212233.zip` quedó respaldado en `C:\VertexBackups` bajo la firma criptográfica SHA-256:
`DAF2F8FC24AC59D378193B2A0D1329A7964C7F99836B5106720CE42DB473268A`.