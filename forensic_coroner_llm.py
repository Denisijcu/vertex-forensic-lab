"""
Perito forense híbrido de Vertex Forensic Lab.

- La CLASIFICACIÓN la decide Python con indicadores duros de agente.
- El LLM local solo redacta el dictamen; si falla o contradice la evidencia, se usa el determinista.
- Re-evalúa automáticamente las sesiones con actividad posterior a su último veredicto.

Uso:
    python forensic_coroner_llm.py            # sesiones nuevas o con actividad nueva
    python forensic_coroner_llm.py --rejudge  # re-evalúa TODAS las sesiones
"""
import os
import re
import sys
import json
import time
import duckdb
import httpx
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT_DIR / "backend"))
from lab_env import DB_PATH, ENTROPY_SQLI_THRESHOLD, CADENCE_THRESHOLD_MS, BURST_GAP_MS  # noqa: E402

LM_STUDIO_URL = os.environ.get("LM_STUDIO_URL", "http://localhost:1234/v1/chat/completions")
MODEL_NAME = os.environ.get("MODEL_NAME", "vertex-core-sec-turn")

# Cadencia (CADENCE_THRESHOLD_MS / BURST_GAP_MS): definida en backend/lab_env.py
AGENT_UA_KEYWORDS = ("LANGCHAIN", "LANGGRAPH", "AUTOGPT", "CREWAI", "AGENT", "SWARM")
LLM_RETRIES = 3

ENGLISH_MARKERS = re.compile(r"\b(the|and|indicate|indicates|suggest|suggests|which|with|activity|is an)\b", re.I)


def init_verdicts_table(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS forensic_verdicts (
            session_fingerprint VARCHAR PRIMARY KEY,
            classification VARCHAR,
            confidence DOUBLE,
            deception_triggered BOOLEAN,
            verdict_json VARCHAR,
            evaluated_at DOUBLE
        );
    """)


def parse_llm_json_safely(raw_text: str) -> dict:
    cleaned = raw_text.strip()
    cleaned = re.sub(r"^```(?:json)?", "", cleaned).strip()
    cleaned = re.sub(r"```$", "", cleaned).strip()
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if match:
        cleaned = match.group(0)
    for candidate in (cleaned, re.sub(r"[\r\n\t]+", " ", cleaned)):
        try:
            return json.loads(candidate, strict=False)
        except Exception:
            continue
    return {}


def build_evidence(ua, cadence_ms, max_ent, tags, in_swarm, hit_canary):
    """
    Devuelve (indicadores_de_agente, notas_de_contexto).
    Solo los indicadores deciden la clasificación; las notas enriquecen el dictamen.
    """
    ua_upper = (ua or "").upper()
    tags = tags or ""
    ind, notes = [], []

    if in_swarm:
        ind.append("participó en una transferencia lateral de Canary Token entre huellas distintas (swarm_lineage)")
    if "LATERAL_SWARM_HANDOFF" in tags:
        ind.append("presentó un Canary Token emitido a otra huella de sesión")
    if "TAMPERED_CANARY" in tags:
        ind.append("presentó un Canary Token con firma HMAC alterada")
    if max_ent >= ENTROPY_SQLI_THRESHOLD:
        ind.append(f"entropía máxima de {max_ent} bits, por encima del umbral de {ENTROPY_SQLI_THRESHOLD} bits")
    if cadence_ms >= CADENCE_THRESHOLD_MS:
        ind.append(f"cadencia mediana de {cadence_ms} ms dentro de ráfaga, compatible con pausas de inferencia "
                   f"(umbral {CADENCE_THRESHOLD_MS:.0f} ms)")
    matched = [k for k in AGENT_UA_KEYWORDS if k in ua_upper]
    if matched:
        ind.append(f"el User-Agent declara un framework agéntico ({', '.join(matched)})")

    # Contexto: lo hace también un escáner clásico, no prueba por sí solo un agente
    if hit_canary:
        notes.append("accedió al endpoint trampa /api/v1/system/config")
    if "SQLI_HIGH_ENTROPY" in tags:
        notes.append("envió cargas de inyección SQL")
    if "ADMIN_SURFACE_PROBE" in tags:
        notes.append("intentó acceder a la superficie de mando SOAR y fue rechazado con 403")
    return ind, notes


def deterministic_reasoning(expected_class, indicators, notes, cadence_ms, max_ent):
    extra = f" Contexto: {'; '.join(notes)}." if notes else ""
    if expected_class == "AUTONOMOUS_AI_AGENT":
        return "Clasificada como agente autónomo porque " + "; ".join(indicators) + "." + extra
    cadencia = (f"su cadencia mediana ({cadence_ms} ms) es mecánica" if cadence_ms > 0
                else "no presenta ráfagas de peticiones consecutivas")
    return (f"Clasificada como escáner tradicional: no participó en transferencias de Canary Token, no declara "
            f"un framework agéntico, su entropía máxima ({max_ent} bits) queda por debajo de "
            f"{ENTROPY_SQLI_THRESHOLD} bits y {cadencia}.{extra}")


CLAIMS_ABOVE = re.compile(r"supera|superior|por encima|excede|\balt[oa]s?\b|elevad[oa]", re.I)
PROMPT_ECHO = re.compile(r"no calific|umbral establecido para considerar|us[aá]ndolos tal cual", re.I)
LEGACY_FORBIDDEN = re.compile(r"agente|enjambre|malicios|malware|sospechos|inusual|an[oó]mal|ataque", re.I)


def reasoning_rejection(text: str, expected_class: str):
    """Devuelve el motivo de rechazo del texto del LLM, o None si es aceptable."""
    if not text or len(text) < 25:
        return "vacío o demasiado corto"
    if len(ENGLISH_MARKERS.findall(text)) >= 2:
        return "no está en español"
    if PROMPT_ECHO.search(text):
        return "repite las instrucciones del prompt"
    # Frase a frase: no puede afirmar que una entropía bajo el umbral lo supera o es alta
    for sentence in re.split(r"(?<=[.;])\s+", text):
        values = [float(x) for x in re.findall(r"(\d+(?:\.\d+)?)\s*bits", sentence)]
        below = [v for v in values if v < ENTROPY_SQLI_THRESHOLD]
        if below and CLAIMS_ABOVE.search(sentence) and not re.search(r"inferior|por debajo|baja", sentence, re.I):
            return f"afirma que {below[0]} bits es alto o supera el umbral"
    if expected_class == "LEGACY_SCANNER" and LEGACY_FORBIDDEN.search(text):
        return "atribuye intención maliciosa o de agente a un escáner"
    return None


def ask_llm(client, payload, fp):
    """Llama a LM Studio con reintentos (cubre la carga JIT del modelo). Devuelve el texto o None."""
    for attempt in range(1, LLM_RETRIES + 1):
        try:
            resp = client.post(LM_STUDIO_URL, json=payload)
            if resp.status_code == 200:
                return resp.json()["choices"][0]["message"]["content"]
            detail = resp.text.strip().replace("\n", " ")[:220]
            print(f"    [!] LM Studio HTTP {resp.status_code} en {fp[:8]} (intento {attempt}/{LLM_RETRIES}): {detail}")
        except Exception as exc:
            print(f"    [!] LM Studio no disponible para {fp[:8]} (intento {attempt}/{LLM_RETRIES}): {type(exc).__name__}")
        if attempt < LLM_RETRIES:
            time.sleep(2.0 * attempt)
    return None


def run_coroner_autopsy(rejudge: bool = False):
    if not os.path.exists(DB_PATH):
        print(f"[!] Bóveda DuckDB no encontrada en {DB_PATH}")
        return

    conn = duckdb.connect(DB_PATH)
    init_verdicts_table(conn)
    try:
        having = "" if rejudge else "HAVING v.evaluated_at IS NULL OR MAX(e.timestamp) > v.evaluated_at"
        sessions = conn.execute(f"""
        SELECT
            e.session_fingerprint,
            e.client_ip,
            MAX(e.user_agent) AS ua,
            COUNT(e.event_id) AS total_reqs,
            ROUND(COALESCE(MEDIAN(e.delta_t_ms) FILTER (WHERE e.delta_t_ms > 0 AND e.delta_t_ms <= {BURST_GAP_MS}), 0), 2) AS cadence_ms,
            ROUND(MAX(e.payload_entropy), 3) AS max_entropy,
            STRING_AGG(DISTINCT e.deception_triggered, ',') AS deception_tags,
            EXISTS(
                SELECT 1 FROM swarm_lineage s
                WHERE (s.scout_fp = e.session_fingerprint OR s.exploit_fp = e.session_fingerprint)
                  AND s.handoff_type = 'LATERAL_SWARM_HANDOFF'
            ) AS in_swarm_lineage,
            BOOL_OR(e.endpoint = '/api/v1/system/config') AS hit_canary_trap
        FROM forensic_evidence e
        LEFT JOIN forensic_verdicts v ON v.session_fingerprint = e.session_fingerprint
        GROUP BY e.session_fingerprint, e.client_ip, v.evaluated_at
        {having}
        """).fetchall()

        if not sessions:
            print("[*] No hay sesiones nuevas ni con actividad nueva pendientes de peritaje.")
            return

        modo = "RE-EVALUACIÓN COMPLETA" if rejudge else "sesiones nuevas o con actividad nueva"
        print(f"[*] Perito ({modo}): {len(sessions)} sesiones con '{MODEL_NAME}'...")
        client = httpx.Client(timeout=60.0)

        verdict_schema = {
            "type": "json_schema",
            "json_schema": {
                "name": "forensic_verdict",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {"reasoning": {"type": "string"}},
                    "required": ["reasoning"],
                    "additionalProperties": False,
                },
            },
        }

        for fp, ip, ua, reqs, cadence_ms, max_ent, tags, in_swarm, hit_canary in sessions:
            cadence_ms = float(cadence_ms or 0.0)
            max_ent = float(max_ent or 0.0)
            indicators, notes = build_evidence(ua, cadence_ms, max_ent, tags, in_swarm, hit_canary)
            is_ai_agent = bool(indicators)
            expected_class = "AUTONOMOUS_AI_AGENT" if is_ai_agent else "LEGACY_SCANNER"
            confidence = 0.95 if is_ai_agent else 0.90
            fallback = deterministic_reasoning(expected_class, indicators, notes, cadence_ms, max_ent)

            ind_txt = "\n".join(f"  - {i}" for i in indicators) or "  - ninguno"
            notes_txt = "\n".join(f"  - {n}" for n in notes) or "  - ninguno"
            prompt = (
                "Redacta en español técnico, en UNA sola oración, el dictamen de esta sesión.\n"
                f"Clasificación ya confirmada por telemetría: {expected_class}.\n"
                f"Indicadores de agente confirmados (úsalos tal cual, no inventes otros):\n{ind_txt}\n"
                f"Contexto adicional:\n{notes_txt}\n"
                f"Datos: {reqs} peticiones, cadencia mediana {cadence_ms} ms, entropía máxima {max_ent} bits "
                f"(umbral {ENTROPY_SQLI_THRESHOLD} bits), User-Agent '{ua}'.\n"
                "No califiques como 'alta' una entropía por debajo del umbral."
            )
            payload = {
                "model": MODEL_NAME,
                "messages": [
                    {"role": "system", "content": "Eres un perito forense de ciberseguridad. Respondes solo JSON y siempre en español."},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.1,
                "response_format": verdict_schema,
            }

            # El dictamen OFICIAL es siempre el determinista (es el que va al acta firmada).
            # El texto del LLM es un comentario no vinculante, y solo se guarda si pasa la validación.
            reasoning, source = fallback, "DETERMINISTA"
            llm_commentary = None
            content = ask_llm(client, payload, fp)
            if content:
                candidate = str(parse_llm_json_safely(content).get("reasoning", "")).strip()
                motivo = reasoning_rejection(candidate, expected_class)
                if motivo is None:
                    llm_commentary = candidate
                else:
                    print(f"    [!] Comentario del LLM descartado para {fp[:8]}: {motivo}")

            verdict_json = json.dumps({
                "classification": expected_class,
                "confidence": confidence,
                "reasoning": reasoning,
                "reasoning_source": source,
                "llm_commentary": llm_commentary,
                "indicators": indicators,
                "context": notes,
                "cadence_median_ms": cadence_ms,
            }, ensure_ascii=False)

            conn.execute("INSERT OR REPLACE INTO forensic_verdicts VALUES (?, ?, ?, ?, ?, ?)",
                         [fp, expected_class, confidence, is_ai_agent, verdict_json, time.time()])
            llm_tag = "comentario LLM válido" if llm_commentary else "sin comentario LLM"
            print(f"    [+] {fp[:8]}... ({ip}) -> {expected_class} ({confidence * 100:.0f}%) [{source}, {llm_tag}]")
    finally:
        conn.close()


if __name__ == "__main__":
    run_coroner_autopsy(rejudge="--rejudge" in sys.argv)
