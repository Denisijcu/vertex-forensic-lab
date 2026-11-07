import os
import sys
import hashlib
import duckdb
from pathlib import Path
from datetime import datetime, timezone

ROOT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT_DIR / "backend"))
from lab_env import DB_PATH  # noqa: E402

REPORTS_DIR = str(ROOT_DIR / "forensic_vault" / "reports")

def generate_autopsy_report():
    if not os.path.exists(DB_PATH):
        print(f"[!] Bóveda no encontrada en {DB_PATH}. Ejecuta el simulador primero.")
        return

    os.makedirs(REPORTS_DIR, exist_ok=True)
    conn = duckdb.connect(DB_PATH, read_only=True)
    
    try:
        tables = [t[0] for t in conn.execute("SHOW TABLES").fetchall()]
        if "forensic_evidence" not in tables:
            print("[!] La tabla forensic_evidence no existe en DuckDB.")
            return

        total_events = conn.execute("SELECT COUNT(*) FROM forensic_evidence").fetchone()[0]
        unique_sessions = conn.execute("SELECT COUNT(DISTINCT session_fingerprint) FROM forensic_evidence").fetchone()[0]
        max_entropy = conn.execute("SELECT MAX(payload_entropy) FROM forensic_evidence").fetchone()[0]
        
        sessions = conn.execute("""
            SELECT session_fingerprint, client_ip, COUNT(*) as reqs, ROUND(AVG(delta_t_ms), 2) as avg_dt
            FROM forensic_evidence
            GROUP BY session_fingerprint, client_ip
        """).fetchall()

        now_utc = datetime.now(timezone.utc)
        timestamp_str = now_utc.strftime("%Y-%m-%d %H:%M:%S UTC")
        
        report_content = f"""# ACTA PERICIAL FORENSE — VERTEX FORENSIC LAB
**Fecha de Emisión:** {timestamp_str}
**Total de Paquetes Capturados:** {total_events}
**Sesiones Únicas Analizadas:** {unique_sessions}
**Entropía Máxima Registrada:** {(max_entropy or 0.0):.4f} bits/símbolo

---

## 📋 Resumen de Sesiones Capturadas
| Fingerprint de Sesión | IP de Origen | Peticiones | Media Delta T (ms) |
|---|---|---|---|
"""
        for fp, ip, reqs, avg_dt in sessions:
            report_content += f"| `{fp}` | `{ip}` | {reqs} | {avg_dt} ms |\n"

        report_content += """
---
*Informe generado automáticamente por el Motor Forense de Vertex Coders LLC.*
"""
        # Calcular Hash SHA-256 del acta para inmutabilidad
        report_hash = hashlib.sha256(report_content.encode("utf-8")).hexdigest()
        filename = f"autopsy_report_{now_utc.strftime('%Y%m%d_%H%M%S')}.md"
        filepath = os.path.join(REPORTS_DIR, filename)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(report_content)
            f.write(f"\n<!-- SHA-256 Fingerprint: {report_hash} -->\n")

        print(f"[+] ¡Autopsia completada sin avisos! Acta generada en: {filepath}")
        print(f"[+] Sello SHA-256 del acta: {report_hash}")

    finally:
        conn.close()

if __name__ == "__main__":
    generate_autopsy_report()