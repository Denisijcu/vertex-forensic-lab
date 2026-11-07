import asyncio
import sys
from pathlib import Path
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    # Configurar los parámetros para ejecutar el servidor MCP localmente vía stdio
    server_params = StdioServerParameters(
        command=sys.executable,
        args=[str(Path(__file__).resolve().parent / "server.py")],
        env=None
    )

    print("[*] Iniciando cliente de prueba MCP para Vertex Forensic Lab...")

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # 1. Inicializar la sesión del protocolo MCP
            await session.initialize()
            print("[+] Sesión MCP inicializada correctamente.\n")
            
            # 2. Listar las herramientas expuestas por el servidor
            print("[*] Consultando herramientas disponibles en el servidor...")
            tools_response = await session.list_tools()
            for tool in tools_response.tools:
                print(f"    - [{tool.name}]: {tool.description}")
            print("-" * 60)

            # 3. Invocar herramienta: Resumen de Veredictos Periciales
            print("\n[*] Invocando herramienta: get_forensic_verdicts_summary...")
            res_verdicts = await session.call_tool("get_forensic_verdicts_summary", {})
            print(f"Resultado:\n{res_verdicts.content[0].text}")
            print("-" * 60)

            # 4. Invocar herramienta: Trazabilidad de Enjambres (Swarm Lineage)
            print("\n[*] Invocando herramienta: get_swarm_handoff_lineage...")
            res_lineage = await session.call_tool("get_swarm_handoff_lineage", {})
            print(f"Resultado:\n{res_lineage.content[0].text}")
            print("-" * 60)

            # 5. Invocar herramienta: Bloqueo de IP con salvaguarda Loopback
            print("\n[*] Invocando herramienta: block_suspicious_ip (IP: 127.0.0.1)...")
            res_block = await session.call_tool("block_suspicious_ip", {
                "ip_address": "127.0.0.1",
                "session_fingerprint": "cli_test_fp"
            })
            print(f"Resultado:\n{res_block.content[0].text}")
            print("-" * 60)

            # 6. Prueba de hardening: intento de inyección de comandos (debe rechazarse)
            print("\n[*] Invocando block_suspicious_ip con IP maliciosa '1.2.3.4; whoami'...")
            res_inj = await session.call_tool("block_suspicious_ip", {
                "ip_address": "1.2.3.4; whoami",
                "session_fingerprint": "cli_test_inj"
            })
            print(f"Resultado:\n{res_inj.content[0].text}")
            print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())