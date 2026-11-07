import os
import duckdb
from fastapi import APIRouter, Depends, HTTPException, Request

from lab_env import DB_PATH, is_admin_client
from session_queries import SESSION_SUMMARY_SQL


def require_admin_client(request: Request) -> None:
    """Defensa en profundidad: la superficie de mando solo responde al HUD local."""
    client_ip = request.client.host if request.client else ""
    if not is_admin_client(client_ip):
        raise HTTPException(status_code=403, detail="Forbidden")


router = APIRouter(dependencies=[Depends(require_admin_client)])


def get_db_path() -> str:
    return DB_PATH


@router.get("/api/telemetry/state")
def get_telemetry_state():
    db_path = get_db_path()
    if not os.path.exists(db_path):
        return {"sessions": [], "lineage": []}

    conn = duckdb.connect(db_path, read_only=True)
    try:
        rows = conn.execute(SESSION_SUMMARY_SQL).fetchall()
        sessions = []

        for r in rows:
            fp = r[0]
            # Últimos 30 eventos de la sesión, en orden cronológico
            timeline_rows = conn.execute("""
                SELECT event_id, endpoint, delta_t_ms, payload_entropy, deception_triggered
                FROM (
                    SELECT event_id, endpoint, delta_t_ms, payload_entropy, deception_triggered, timestamp
                    FROM forensic_evidence
                    WHERE session_fingerprint = ?
                    ORDER BY timestamp DESC
                    LIMIT 30
                ) ORDER BY timestamp ASC
            """, [fp]).fetchall()

            sessions.append({
                "session_fingerprint": fp,
                "client_ip": r[1],
                "total_requests": r[3],
                "cadence_ms": r[4],
                "max_entropy": r[5],
                "classification": r[7],
                "confidence": round(float(r[8]) * 100, 1),
                "is_blocked": bool(r[11]),
                "firewall_rule": r[10],
                "enforcement_status": r[11],
                "timeline": [
                    {"event_id": t[0], "endpoint": t[1], "delta_t_ms": t[2], "entropy": t[3], "deception": t[4]}
                    for t in timeline_rows
                ],
            })

        lineage = []
        for l in conn.execute("""
            SELECT handoff_id, detected_at, handoff_type, scout_fp, scout_ip, exploit_fp, exploit_ip,
                   token_transit_ms, endpoint_targeted
            FROM swarm_lineage
            ORDER BY detected_at DESC
        """).fetchall():
            lineage.append({
                "handoff_id": l[0],
                "detected_at": l[1],
                "handoff_type": l[2],
                "scout_fp": l[3],
                "scout_ip": l[4],
                "exploit_fp": l[5],
                "exploit_ip": l[6],
                "token_transit_ms": round(float(l[7]), 2),
                "endpoint_targeted": l[8],
            })

        return {"sessions": sessions, "lineage": lineage}
    finally:
        conn.close()
