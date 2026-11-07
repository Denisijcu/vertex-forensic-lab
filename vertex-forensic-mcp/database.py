import os
import sys
import duckdb
from pathlib import Path

# Misma resolución de bóveda que el backend (lab_env.py)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))
from lab_env import DB_PATH  # noqa: E402

def get_db_connection():
    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(f"Bóveda DuckDB no encontrada en: {DB_PATH}")
    return duckdb.connect(DB_PATH, read_only=True)

def fetch_recent_evidence(limit: int = 10):
    conn = get_db_connection()
    try:
        query = "SELECT event_id, timestamp, client_ip, session_fingerprint, endpoint, delta_t_ms, payload_entropy, deception_triggered FROM forensic_evidence ORDER BY timestamp DESC LIMIT ?"
        return conn.execute(query, [limit]).fetchall()
    finally:
        conn.close()

def fetch_verdicts():
    conn = get_db_connection()
    try:
        query = "SELECT session_fingerprint, classification, confidence, deception_triggered, evaluated_at FROM forensic_verdicts"
        return conn.execute(query).fetchall()
    finally:
        conn.close()

def fetch_swarm_lineage():
    conn = get_db_connection()
    try:
        query = "SELECT handoff_id, detected_at, handoff_type, scout_fp, exploit_fp, token_transit_ms, endpoint_targeted FROM swarm_lineage"
        return conn.execute(query).fetchall()
    finally:
        conn.close()