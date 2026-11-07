# REFERENCIA RÁPIDA DE MANDO — VERTEX FORENSIC LAB v1.3

Ubicación base: `E:\vertex-forensic-lab`. Invoca siempre los scripts con `powershell -ExecutionPolicy Bypass -File`.

## Ciclo de vida (PowerShell)

| Acción | Comando (desde `E:\vertex-forensic-lab`) |
| --- | --- |
| Arrancar (genera `.env` y la regla WSL) | `powershell -ExecutionPolicy Bypass -File .\Start-VertexLab.ps1` |
| Parar (libera 8000 y 4200) | `powershell -ExecutionPolicy Bypass -File .\Stop-VertexLab.ps1` |
| Parar y quitar los bloqueos SOAR | `powershell -ExecutionPolicy Bypass -File .\Stop-VertexLab.ps1 -RemoveBlocks` |
| Parar y quitar la regla de entrada | `powershell -ExecutionPolicy Bypass -File .\Stop-VertexLab.ps1 -RemoveIngress` |
| Release firmado | `powershell -ExecutionPolicy Bypass -File .\Invoke-VertexRelease.ps1` |

Las operaciones con reglas de firewall requieren **PowerShell como Administrador**.

## Asalto desde Parrot (WSL2, NAT)

```bash
tr -d '\r' < /mnt/e/vertex-forensic-lab/tmp/swarm_assault.sh > /tmp/swarm_assault.sh
bash /tmp/swarm_assault.sh
```

## Qué debe pasar

| Fase | Resultado esperado |
| --- | --- |
| 1 Nikto | HTTP 500 (error SQL señuelo), tiempos cortos |
| 2 Scout | Canary Token `vx_cnry_...` exfiltrado |
| 3 Exploit | HTTP 200 `PARTIAL_DUMP`; el tarpit retiene ≈3.3 s → 6 s → 6 s (tope) |
| 4 Mando | HTTP 403 en `/api/telemetry/state` y `/api/actions/firewall-block` (≈6 s cada uno, tarpit) |
| HUD | Sesiones con IP `172.x.x.x` y handoff Scout → Exploit en el panel rojo |
| Aislar | Botón **🛡️ FIREWALL ACTIVO**; al repetir el asalto, Parrot recibe timeout |

## Comprobar reglas de firewall

```powershell
Get-NetFirewallRule -DisplayName "VERTEX*" | Select-Object DisplayName, Direction, Action, Enabled
```
