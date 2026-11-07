import sys
import json
import duckdb
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))
from lab_env import DB_PATH  # noqa: E402

def main():
    conn = duckdb.connect(DB_PATH, read_only=True)
    try:
        rows = conn.execute(
            "SELECT session_fingerprint, classification, confidence, verdict_json FROM forensic_verdicts"
        ).fetchall()
        
        print(f"\n================ AUDITORÍA DE VEREDICTOS ({len(rows)} sesiones) ================")
        for r in rows:
            fp, classification, confidence, raw_json = r
            parsed = json.loads(raw_json)
            reasoning = parsed.get("reasoning", "Sin razonamiento explícito")
            
            print(f"[*] Sesión     : {fp}")
            print(f"    Veredicto  : {classification} (Certeza: {confidence * 100:.1f}%)")
            print(f"    Razonamiento: {reasoning}")
            print(f"    Origen     : {parsed.get('reasoning_source', 'LLM (v1.2)')}")
            print("-" * 65)
    finally:
        conn.close()

if __name__ == "__main__":
    main()