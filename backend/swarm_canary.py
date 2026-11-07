import os
import sys
import time
import hmac
import hashlib
import base64
import secrets
from typing import Optional

import lab_env  # noqa: F401  (carga .env antes de leer el secreto)

_secret = os.environ.get("VERTEX_CANARY_SECRET", "").strip()
if not _secret:
    # Sin secreto configurado: uno efímero por proceso (los tokens mueren al reiniciar)
    _secret = secrets.token_hex(32)
    print("[!] VERTEX_CANARY_SECRET no definido: usando secreto efímero. "
          "Ejecuta Start-VertexLab.ps1 para generar .env.", file=sys.stderr)
SECRET_KEY = _secret.encode("utf-8")

def mint_canary_token(scout_fingerprint: str, scout_ip: str) -> str:
    """
    Emite un token canario firmado con HMAC-SHA256 que incrusta la huella
    de sesión (FP), la IP original y el timestamp exacto de emisión.
    """
    ts = int(time.time() * 1000)
    payload = f"{scout_fingerprint}|{scout_ip}|{ts}"
    payload_b64 = base64.urlsafe_b64encode(payload.encode("utf-8")).decode("utf-8").rstrip("=")
    
    signature = hmac.new(SECRET_KEY, payload_b64.encode("utf-8"), hashlib.sha256).hexdigest()[:16]
    return f"vx_cnry_{payload_b64}.{signature}"

def verify_and_trace_canary(token_str: str, current_fp: str, current_ip: str) -> Optional[dict]:
    """
    Verifica la firma HMAC del token. Si es válido, extrae los metadatos del nodo
    Scout original y determina si ocurrió un movimiento lateral en el enjambre.
    """
    if not token_str or not token_str.startswith("vx_cnry_") or "." not in token_str:
        return None

    try:
        raw_part, recv_sig = token_str[8:].split(".", 1)
        expected_sig = hmac.new(SECRET_KEY, raw_part.encode("utf-8"), hashlib.sha256).hexdigest()[:16]
        
        if not hmac.compare_digest(recv_sig, expected_sig):
            return {"status": "TAMPERED_CANARY", "lateral_movement": True}

        # Restaurar padding Base64 y decodificar
        padding = "=" * (-len(raw_part) % 4)
        decoded = base64.urlsafe_b64decode((raw_part + padding).encode("utf-8")).decode("utf-8")
        scout_fp, scout_ip, mint_ts_str = decoded.split("|")
        
        now_ms = int(time.time() * 1000)
        transit_ms = float(now_ms - int(mint_ts_str))

        handoff_type = (
            "LATERAL_SWARM_HANDOFF" 
            if scout_fp != current_fp 
            else "SINGLE_AGENT_REPLAY"
        )

        return {
            "status": "VALID_CANARY_TRIGGER",
            "handoff_type": handoff_type,
            "scout_fp": scout_fp,
            "scout_ip": scout_ip,
            "exploit_fp": current_fp,
            "exploit_ip": current_ip,
            "token_transit_ms": round(transit_ms, 2)
        }
    except Exception:
        return None