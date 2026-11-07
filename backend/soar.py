"""
Contención SOAR compartida (backend FastAPI + servidor MCP).

- Valida la IP con ipaddress (sin concatenar nada al shell: lista de argumentos).
- Loopback -> SIMULATED_LOOPBACK (protege Angular/FastAPI/LM Studio).
- Rechaza IPs que no tiene sentido bloquear (0.0.0.0, multicast, broadcast).
- No duplica reglas: si la regla ya existe en netsh, la reporta como ALREADY_ENFORCED.
- Sin netsh (Docker/Linux) o sin Admin -> LOGICAL_BLOCK_ONLY.
- Persiste la acción en DuckDB (tabla soar_actions).
"""
import time
import subprocess
import duckdb

from lab_env import DB_PATH, normalize_ip

SOAR_TABLE_DDL = """
CREATE TABLE IF NOT EXISTS soar_actions (
    session_fingerprint VARCHAR PRIMARY KEY,
    ip_address VARCHAR,
    rule_name VARCHAR,
    enforcement_status VARCHAR,
    reason VARCHAR,
    applied_at DOUBLE
);
"""


class SoarValidationError(ValueError):
    pass


def validate_target_ip(ip_str: str) -> str:
    try:
        ip = normalize_ip(ip_str)
    except ValueError:
        raise SoarValidationError(f"'{ip_str}' no es una dirección IP válida.")
    if ip.is_unspecified or ip.is_multicast or str(ip) == "255.255.255.255":
        raise SoarValidationError(f"La IP {ip} no es un objetivo de bloqueo válido.")
    return str(ip)


def _netsh(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(["netsh", "advfirewall", "firewall", *args],
                          capture_output=True, text=True, timeout=15)


def _rule_exists(rule_name: str) -> bool:
    res = _netsh(["show", "rule", f"name={rule_name}"])
    return res.returncode == 0


def apply_block(ip_str: str, session_fingerprint: str, reason: str, rule_prefix: str = "VERTEX_BLOCK") -> dict:
    valid_ip = validate_target_ip(ip_str)
    fp = (session_fingerprint or "unknown")[:8]
    rule_name = f"{rule_prefix}_{fp}_{valid_ip}"

    if normalize_ip(valid_ip).is_loopback:
        status = "SIMULATED_LOOPBACK"
        msg = f"Salvaguarda loopback activa: regla '{rule_name}' registrada en DuckDB y simulada para proteger localhost."
    else:
        try:
            if _rule_exists(rule_name):
                status = "ALREADY_ENFORCED"
                msg = f"La regla '{rule_name}' ya existe en Windows Firewall; no se duplica."
            else:
                res = _netsh(["add", "rule", f"name={rule_name}", "dir=in",
                              "action=block", f"remoteip={valid_ip}"])
                if res.returncode == 0:
                    status = "ENFORCED_NETSH"
                    msg = f"IP {valid_ip} bloqueada en Windows Firewall ({rule_name})."
                else:
                    status = "LOGICAL_BLOCK_ONLY"
                    msg = (f"Regla '{rule_name}' registrada solo en DuckDB: netsh la rechazó "
                           f"(¿Uvicorn sin Administrador?). Detalle: {(res.stdout or res.stderr).strip()[:160]}")
        except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
            status = "LOGICAL_BLOCK_ONLY"
            msg = f"Regla '{rule_name}' registrada solo en DuckDB: netsh no disponible ({type(exc).__name__})."

    conn = duckdb.connect(DB_PATH)
    try:
        conn.execute(SOAR_TABLE_DDL)
        conn.execute("INSERT OR REPLACE INTO soar_actions VALUES (?, ?, ?, ?, ?, ?)",
                     [session_fingerprint, valid_ip, rule_name, status, reason, time.time()])
    finally:
        conn.close()

    return {"status": status, "rule_name": rule_name, "ip_blocked": valid_ip, "message": msg}
