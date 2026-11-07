import os
import sys
import json
import hashlib
import ipaddress
import duckdb
from datetime import datetime, timezone
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT_DIR / "backend"))
from lab_env import DB_PATH  # noqa: E402

REPORTS_DIR = ROOT_DIR / "forensic_vault" / "reports"

def compute_file_sha256(filepath: str) -> str:
    """Calcula el hash SHA-256 físico del archivo DuckDB en disco."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()

def compute_evidence_chain_hash(conn: duckdb.DuckDBPyConnection) -> tuple[str, int]:
    """
    Construye un hash encadenado (Hash-Chain) sobre todos los paquetes ordenados
    cronológicamente para sellar la línea de tiempo contra alteraciones.
    """
    rows = conn.execute("""
        SELECT event_id, timestamp, session_fingerprint, payload_entropy, deception_triggered
        FROM forensic_evidence
        ORDER BY timestamp ASC, event_id ASC
    """).fetchall()

    chain_digest = hashlib.sha256(b"VERTEX_FORENSIC_GENESIS_SEED").hexdigest()
    for r in rows:
        record_str = f"{chain_digest}|{r[0]}|{r[1]:.6f}|{r[2]}|{r[3]}|{r[4]}"
        chain_digest = hashlib.sha256(record_str.encode("utf-8")).hexdigest()

    return chain_digest, len(rows)

def escape_md_cell(val: str) -> str:
    """Impide que un payload malicioso rompa las tablas Markdown del informe."""
    if not val:
        return "-"
    cleaned = str(val).replace("|", "\\|").replace("\n", " ").replace("\r", "")
    return cleaned[:90] + ("..." if len(cleaned) > 90 else "")

def generate_forensic_markdown_report() -> Path:
    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(f"No se encontró la base de evidencia en {DB_PATH}")

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    now_utc = datetime.now(timezone.utc)
    case_id = f"VX-INC-{now_utc.strftime('%Y%m%d-%H%M%S')}"
    report_path = REPORTS_DIR / f"Acta_Forense_{case_id}.md"

    # 1. Sellos criptográficos previos a la consulta
    db_file_hash = compute_file_sha256(DB_PATH)
    conn = duckdb.connect(DB_PATH, read_only=True)

    try:
        chain_hash, total_events = compute_evidence_chain_hash(conn)

        # 2. Consulta de métricas agregadas por sesión
        sessions = conn.execute("""
            SELECT 
                session_fingerprint,
                client_ip,
                COUNT(*) AS reqs,
                ROUND(AVG(delta_t_ms), 2) AS avg_dt,
                ROUND(STDDEV(delta_t_ms), 2) AS std_dt,
                ROUND(MAX(payload_entropy), 3) AS max_ent,
                LIST(DISTINCT deception_triggered) AS tags
            FROM forensic_evidence
            GROUP BY session_fingerprint, client_ip
            ORDER BY avg_dt DESC
        """).fetchall()

        # 3. Consulta de linaje HMAC (Enjambres multi-agente)
        tables = [t[0] for t in conn.execute("SHOW TABLES").fetchall()]
        swarm_rows = []
        if "swarm_lineage" in tables:
            swarm_rows = conn.execute("""
                SELECT 
                    handoff_id,
                    handoff_type,
                    scout_fp,
                    scout_ip,
                    exploit_fp,
                    exploit_ip,
                    ROUND(token_transit_ms, 2) AS transit_ms,
                    endpoint_targeted
                FROM swarm_lineage
                ORDER BY detected_at ASC
            """).fetchall()

        # 4. Consulta de dictámenes emitidos por el LLM Local
        verdict_rows = []
        if "forensic_verdicts" in tables:
            verdict_rows = conn.execute("""
                SELECT
                    session_fingerprint,
                    evaluated_at,
                    classification,
                    confidence,
                    deception_triggered,
                    verdict_json
                FROM forensic_verdicts
                ORDER BY evaluated_at DESC
            """).fetchall()

    finally:
        conn.close()

    # =====================================================================
    # CONSTRUCCIÓN DEL DOCUMENTO PERICIAL EN MARKDOWN
    # =====================================================================
    lines = [
        f"# ACTA DE AUDITORÍA FORENSE Y TELEMETRÍA DE AGENTES IA",
        f"**Entidad Auditora:** Unidad de Inteligencia Ofensiva & Defensa Activa — Vertex Coders LLC  ",
        f"**Identificador de Caso:** `{case_id}`  ",
        f"**Fecha de Emisión (UTC):** `{now_utc.strftime('%Y-%m-%d %H:%M:%S UTC')}`  ",
        f"**Clasificación del Documento:** `CONFIDENCIAL // CADENA DE CUSTODIA CRIPTOGRÁFICA`",
        "",
        "## 1. Manifiesto de Cadena de Custodia (SHA-256)",
        "Los siguientes resúmenes criptográficos certifican la integridad inmutable de la base de datos de telemetría y la secuencia cronológica de paquetes al momento de emitir este dictamen:",
        "",
        "| Artefacto Bajo Custodia | Algoritmo | Valor de Verificación / Hash |",
        "| :--- | :--- | :--- |",
        f"| Bóveda de Telemetría (`telemetry.duckdb`) | `SHA-256 (Archivo)` | `{db_file_hash}` |",
        f"| Raíz de Línea Temporal ({total_events} eventos) | `SHA-256 (Hash-Chain)` | `{chain_hash}` |",
        "",
        "## 2. Matriz Estadística de Sesiones Capturadas",
        "Análisis diferencial de cadencia temporal ($\\Delta t$), desviación estándar ($\\sigma$) y entropía de Shannon ($H$) por huella de sesión:",
        "",
        "| Huella de Sesión (`FP`) | IP Origen | Peticiones | Media $\\Delta t$ (ms) | Desviación $\\sigma$ (ms) | Entropía Máx (bits) | Sensores / Tarpit Activados |",
        "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |"
    ]

    for s in sessions:
        fp, ip, reqs, avg_dt, std_dt, max_ent, tags = s
        std_val = f"{std_dt:.2f}" if std_dt is not None else "0.00"
        tags_str = ", ".join(tags) if tags else "STANDARD_PROBE"
        lines.append(
            f"| `{fp}` | `{ip}` | {reqs} | {avg_dt:.2f} | {std_val} | {max_ent:.3f} | `{escape_md_cell(tags_str)}` |"
        )

    lines.extend([
        "",
        "## 3. Trazabilidad de Enjambre y Movimiento Lateral (HMAC Canary Lineage)",
    ])

    if swarm_rows:
        lines.extend([
            "Evidencia criptográfica de compartición de credenciales (`vx_cnry_`) entre nodos de reconocimiento y nodos de explotación:",
            "",
            "| ID Evento | Tipo de Coordinación | Nodo Scout (Origen) | Nodo Exploit (Destino) | Tránsito Bus (ms) | Endpoint Atacado |",
            "| :--- | :--- | :--- | :--- | :--- | :--- |"
        ])
        for sw in swarm_rows:
            hid, htype, s_fp, s_ip, e_fp, e_ip, transit, ep = sw
            lines.append(
                f"| `{hid}` | **{htype}** | `{s_fp}` ({s_ip}) | `{e_fp}` ({e_ip}) | {transit:.1f} ms | `{ep}` |"
            )
    else:
        lines.append("*No se registraron transferencias laterales de Canary Tokens entre sesiones distintas en este ciclo.*")

    lines.extend([
        "",
        "## 4. Dictámenes Periciales (perito híbrido)",
    ])

    if verdict_rows:
        for v in verdict_rows:
            v_fp, v_ts, v_class, v_conf, v_trap, v_json_str = v
            try:
                vd = json.loads(v_json_str or "{}")
            except Exception:
                vd = {}
            lines.extend([
                f"### Expediente de Sesión: `{v_fp}`",
                f"* **Clasificación del Actor:** `{v_class}` (Certeza: **{float(v_conf) * 100:.1f}%**)",
                f"* **Indicadores de Agente Activados:** `{'SÍ' if v_trap else 'NO'}`",
                f"* **Dictamen ({vd.get('reasoning_source', 'LLM')}):** {escape_md_cell(vd.get('reasoning', 'Sin dictamen'))}",
            ])
            for idx, ind in enumerate(vd.get("indicators", []), 1):
                lines.append(f"  {idx}. {escape_md_cell(ind)}")
            lines.append("")
    else:
        lines.append("*Sin dictámenes almacenados en `forensic_verdicts`.*")

    # =====================================================================
    # 5. ANEXO DE COMANDOS DE CONTENCIÓN Y SELLO FINAL DEL DOCUMENTO
    # =====================================================================
    lines.extend([
        "## 5. Reglas de Contención Inmediata (Firewall & Reverse Proxy)",
        "Comandos generados automáticamente para aislar las direcciones IP identificadas en la boveda forense:",
        "",
        "```powershell"
    ])
    seen_ips = set()
    for s in sessions:
        try:
            ip_obj = ipaddress.ip_address(s[1])
        except ValueError:
            continue
        if not ip_obj.is_loopback:
            seen_ips.add(str(ip_obj))
    if not seen_ips:
        lines.append("# Sin IPs externas: todas las sesiones son loopback (no se bloquean).")
    for ip in sorted(seen_ips):
        lines.append(f'netsh advfirewall firewall add rule name="VX_Block_Hostile_Agent_{ip}" dir=in action=block remoteip={ip}')
    lines.extend([
        "```",
        ""
    ])

    body_content = "\n".join(lines)
    report_signature = hashlib.sha256(body_content.encode("utf-8")).hexdigest()

    footer = (
        f"---\n"
        f"**SELLO DE INTEGRIDAD DEL REPORTE (SHA-256):** `{report_signature}`  \n"
        f"*Generado de forma autónoma por Vertex Forensic Coroner Engine.*"
    )

    final_document = f"{body_content}\n{footer}\n"
    report_path.write_text(final_document, encoding="utf-8")
    return report_path

if __name__ == "__main__":
    out_file = generate_forensic_markdown_report()
    print(f"[+] Acta Pericial compilada y firmada con éxito en: {out_file}")