# LEGADO: puente HTTP de solo lectura (puerto 8001). El servidor MCP oficial es server.py (stdio).
import os
import sys
import duckdb
from pathlib import Path
from typing import Any
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))
from lab_env import DB_PATH  # noqa: E402

app = FastAPI(title="Vertex Forensic MCP HTTP Bridge (legacy)")

class MCPQueryRequest(BaseModel):
    tool: str
    arguments: dict[str, Any] = {}

@app.post("/mcp/v1/call")
def handle_mcp_call(payload: MCPQueryRequest):
    if not os.path.exists(DB_PATH):
        raise HTTPException(status_code=404, detail="Bóveda DuckDB no inicializada.")

    conn = duckdb.connect(DB_PATH, read_only=True)
    try:
        if payload.tool == "get_telemetry_summary":
            total = conn.execute("SELECT COUNT(*) FROM forensic_evidence").fetchone()[0]
            sessions = conn.execute("SELECT COUNT(DISTINCT session_fingerprint) FROM forensic_evidence").fetchone()[0]
            return {"total_events": total, "unique_sessions": sessions}
            
        elif payload.tool == "query_high_entropy_sessions":
            threshold = payload.arguments.get("threshold", 4.0)
            rows = conn.execute("""
                SELECT DISTINCT session_fingerprint, client_ip, MAX(payload_entropy) as max_ent
                FROM forensic_evidence
                GROUP BY session_fingerprint, client_ip
                HAVING max_ent >= ?
            """, [threshold]).fetchall()
            return [{"fingerprint": r[0], "ip": r[1], "max_entropy": r[2]} for r in rows]
            
        else:
            raise HTTPException(status_code=400, detail=f"Herramienta MCP desconocida: {payload.tool}")
    finally:
        conn.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8001)