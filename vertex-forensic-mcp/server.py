import sys
from pathlib import Path

# Reutilizar la configuración y el módulo SOAR del backend (una sola implementación)
BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from mcp.server.fastmcp import FastMCP  # noqa: E402

from soar import apply_block, SoarValidationError  # noqa: E402
from database import fetch_recent_evidence, fetch_verdicts, fetch_swarm_lineage  # noqa: E402

mcp = FastMCP("Vertex Forensic MCP Server")


@mcp.tool()
def get_recent_forensic_events(limit: int = 10) -> str:
    """Obtiene los eventos de telemetría más recientes registrados en la bóveda DuckDB."""
    limit = max(1, min(int(limit), 200))
    rows = fetch_recent_evidence(limit)
    if not rows:
        return "No hay registros de telemetría en la bóveda."
    return "\n".join(
        f"ID: {r[0]} | Time: {r[1]} | IP: {r[2]} | FP: {r[3]} | Endpoint: {r[4]} | "
        f"Δt: {r[5]}ms | Entropía: {r[6]} | Tags: {r[7]}"
        for r in rows
    )


@mcp.tool()
def get_forensic_verdicts_summary() -> str:
    """Devuelve el resumen de peritajes y clasificaciones de sesiones (AUTONOMOUS_AI_AGENT vs LEGACY_SCANNER)."""
    rows = fetch_verdicts()
    if not rows:
        return "No hay veredictos periciales emitidos todavía."
    return "\n".join(
        f"Session FP: {r[0]} | Clasificación: {r[1]} | Certeza: {r[2] * 100:.1f}% | Engaño: {r[3]}"
        for r in rows
    )


@mcp.tool()
def get_swarm_handoff_lineage() -> str:
    """Analiza la trazabilidad de enjambres y transferencias laterales (handoffs) entre nodos Scout y Exploit."""
    rows = fetch_swarm_lineage()
    if not rows:
        return "No se han detectado trazas de enjambres en la bóveda."
    return "\n".join(
        f"Handoff: {r[0]} | Tipo: {r[2]} | Scout: {r[3][:8]}... -> Exploit: {r[4][:8]}... | "
        f"Tránsito: {r[5]}ms | Target: {r[6]}"
        for r in rows
    )


@mcp.tool()
def block_suspicious_ip(ip_address: str, session_fingerprint: str = "mcp_agent") -> str:
    """Ejecuta un bloqueo activo en el Firewall de Windows (netsh) y lo persiste en la bóveda DuckDB."""
    try:
        result = apply_block(ip_address, session_fingerprint, "MCP_AGENT_CONTAINMENT", "VERTEX_MCP_BLOCK")
    except SoarValidationError as exc:
        return f"Error de validación: {exc}"
    return f"[{result['status']}] {result['message']}"


if __name__ == "__main__":
    mcp.run()
