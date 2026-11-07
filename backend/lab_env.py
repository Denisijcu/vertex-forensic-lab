"""
Carga de configuración del laboratorio (sin dependencias externas).

Orden de precedencia:
  1. Variables de entorno ya definidas (Docker / PowerShell)  -> mandan siempre
  2. Archivo E:\\vertex-forensic-lab\\.env                      -> solo rellena las que falten

Este módulo debe importarse ANTES que swarm_canary, telemetry_api, etc.
"""
import os
import ipaddress
from pathlib import Path

LAB_ROOT = Path(__file__).resolve().parent.parent


def load_dotenv_file(path: Path) -> None:
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


load_dotenv_file(LAB_ROOT / ".env")

# ---------------------------------------------------------------------
# Bóveda DuckDB: se respeta DB_PATH si viene definido (Docker: /app/vault/...)
# ---------------------------------------------------------------------
DB_PATH = os.environ.get("DB_PATH") or str((LAB_ROOT / "forensic_vault" / "telemetry.duckdb").resolve())
os.environ["DB_PATH"] = DB_PATH
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

# ---------------------------------------------------------------------
# Umbral único de entropía (bits/símbolo) — el mismo que documenta el Informe Técnico
# ---------------------------------------------------------------------
ENTROPY_SQLI_THRESHOLD = float(os.environ.get("VERTEX_ENTROPY_THRESHOLD", "4.5"))

# Cadencia: mediana de Δt dentro de ráfagas (se descartan pausas mayores entre corridas)
CADENCE_THRESHOLD_MS = 1000.0
BURST_GAP_MS = 30000.0

# ---------------------------------------------------------------------
# Superficie de administración (/api/telemetry y /api/actions)
# Solo loopback por defecto. En Docker se añade el gateway del bridge.
# ---------------------------------------------------------------------
_extra = os.environ.get("VERTEX_ADMIN_ALLOWED_CIDRS", "")
ADMIN_ALLOWED_NETS = [ipaddress.ip_network(c.strip(), strict=False) for c in _extra.split(",") if c.strip()]


def normalize_ip(ip_str: str):
    """Devuelve un objeto ip_address, desenvolviendo IPv4 mapeada en IPv6 (::ffff:a.b.c.d)."""
    ip = ipaddress.ip_address(ip_str.strip())
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped:
        return ip.ipv4_mapped
    return ip


def is_admin_client(ip_str: str) -> bool:
    try:
        ip = normalize_ip(ip_str)
    except ValueError:
        return False
    if ip.is_loopback:
        return True
    return any(ip in net for net in ADMIN_ALLOWED_NETS)
