# Vertex Swarm Emulator

Generador de tráfico adversario para el honeypot:

1. **Fase 1:** escáner lineal tradicional con cadencia mecánica (20–35 ms).
2. **Fase 2:** enjambre Scout → Exploit. El Scout roba el Canary Token y el Exploit lo usa con cinco mutaciones SQLi y pausas de inferencia simuladas (1.1–2.25 s).

## Uso

En Docker (perfil `attack`), desde `E:\vertex-forensic-lab`:

```powershell
docker compose --profile attack up agent-simulator
```

En local, contra el gateway en `localhost:8000`, desde `E:\vertex-forensic-lab\simulator`:

```powershell
python agent_emu.py
```

El destino se lee de `TARGET_URL` (o `TARGET_HOST`); por defecto es `http://127.0.0.1:8000`.
