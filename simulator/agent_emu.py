import os
import time
import random
import asyncio
import httpx

# docker-compose define TARGET_URL; TARGET_HOST se mantiene por compatibilidad
TARGET_HOST = os.environ.get("TARGET_URL") or os.environ.get("TARGET_HOST", "http://127.0.0.1:8000")

async def simulate_legacy_scanner():
    """
    Fase 1: Escáner tradicional (ej. Nikto / Nuclei).
    Cadencia mecánica ultrarrápida (Delta T ~ 20-35ms) y baja adaptabilidad.
    """
    print("\n[*] [FASE 1] Iniciando ráfaga de Escáner Lineal Tradicional...")
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; LegacyScanner/2.1; +http://scanner.local)",
        "X-Swarm-Node": "scanner-static-00"
    }
    endpoints = [
        "/api/v1/system/config",
        "/api/v2/internal/vault?node_id=1",
        "/api/v2/internal/vault?node_id=2",
        "/api/v2/internal/vault?node_id=3",
        "/api/v2/internal/vault?node_id=4"
    ]

    async with httpx.AsyncClient(base_url=TARGET_HOST, timeout=10.0) as client:
        for ep in endpoints:
            t0 = time.perf_counter()
            resp = await client.get(ep, headers=headers)
            dt = (time.perf_counter() - t0) * 1000.0
            print(f"    -> [SCANNER] GET {ep} | Status: {resp.status_code} | Latencia total: {dt:.1f}ms")
            await asyncio.sleep(random.uniform(0.015, 0.035))

async def simulate_ai_agent_swarm():
    """
    Fase 2: Enjambre Multi-Agente IA (Ciclo ReAct: Reason + Act).
    - El nodo SCOUT descubre el Canary Token en /api/v1/system/config.
    - Transfiere el token lateralmente al nodo EXPLOIT WORKER.
    - El nodo EXPLOIT muta payloads SQLi tras pausas estocásticas de inferencia LLM (900ms - 2200ms).
    """
    print("\n[*] [FASE 2] Desplegando Enjambre Multi-Agente IA (Scout -> Exploit Handoff)...")
    
    scout_headers = {
        "User-Agent": "Python-httpx/0.28.0 (LangGraph-Autonomous-Agent/1.4)",
        "X-Swarm-Node": "scout-alpha-01"
    }
    exploit_headers = {
        "User-Agent": "Python-httpx/0.28.0 (LangGraph-Autonomous-Agent/1.4)",
        "X-Swarm-Node": "exploit-omega-99"
    }

    async with httpx.AsyncClient(base_url=TARGET_HOST, timeout=15.0) as client:
        # 1. Nodo Scout realiza reconocimiento y extrae el Canary Token
        print("    [SCOUT] Reconociendo superficie en /api/v1/system/config ...")
        r_scout = await client.get("/api/v1/system/config", headers=scout_headers)
        data = r_scout.json()
        canary_token = data.get("debug_token_hint", "")
        vault_ep = data.get("vault_endpoint", "/api/v2/internal/vault")
        print(f"    [SCOUT] Canary Token extraído: {canary_token}")

        # Pausa de coordinación en el bus de memoria del enjambre
        await asyncio.sleep(random.uniform(0.95, 1.45))

        # 2. Nodo Exploit recibe el Canary Token y lanza ataque adaptativo
        exploit_headers["Authorization"] = f"Bearer {canary_token}"
        
        mutations = [
            "105",
            "105'",
            "105' OR '1'='1",
            "105' UNION SELECT null, version(), current_user--",
            "105' UNION SELECT key_hash, secret_blob FROM vault_keys WHERE 'x'='x--"
        ]

        for idx, payload in enumerate(mutations, start=1):
            # Simulación de tiempo de inferencia LLM (generación de tokens ReAct)
            llm_think_sec = random.uniform(1.10, 2.25)
            print(f"    [EXPLOIT-LLM] Razonando mutación #{idx} (Inferencia: {llm_think_sec*1000:.0f}ms)...")
            await asyncio.sleep(llm_think_sec)

            t0 = time.perf_counter()
            r_exp = await client.get(
                vault_ep, 
                params={"node_id": payload}, 
                headers=exploit_headers
            )
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            print(
                f"    -> [EXPLOIT] Payload: {payload[:32]}... | "
                f"Status: {r_exp.status_code} | Respuesta+Tarpit: {elapsed_ms:.1f}ms"
            )

async def main():
    print("==================================================================")
    print("   VERTEX SWARM EMULATOR // GENERADOR DE TRÁFICO ADVERSARIO")
    print("==================================================================")
    await simulate_legacy_scanner()
    await simulate_ai_agent_swarm()
    print("\n[+] Simulación finalizada. Evidencia lista en DuckDB para autopsia.")

if __name__ == "__main__":
    asyncio.run(main())