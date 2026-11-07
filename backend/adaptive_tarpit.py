import asyncio
from collections import defaultdict

class AdaptiveTarpitEngine:
    def __init__(self):
        # Registra el nivel de sospecha acumulado por huella de sesión
        self.suspicion_scores: dict[str, int] = defaultdict(int)

    def register_anomaly(self, session_fp: str, weight: int = 1) -> int:
        self.suspicion_scores[session_fp] += weight
        return self.suspicion_scores[session_fp]

    def get_delay_seconds(self, session_fp: str) -> float:
        score = self.suspicion_scores.get(session_fp, 0)
        if score <= 1:
            return 0.0
        # Retraso exponencial controlado (máximo 6.0 segundos por petición en laboratorio)
        return min(0.35 * (1.75 ** (score - 1)), 6.0)

    async def apply_tarpit_if_needed(self, session_fp: str) -> float:
        delay_sec = self.get_delay_seconds(session_fp)
        if delay_sec > 0:
            await asyncio.sleep(delay_sec)
        return round(delay_sec * 1000.0, 2)

tarpit_engine = AdaptiveTarpitEngine()