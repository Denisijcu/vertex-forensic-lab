# Apéndice A — Comandos de operación

Todos los comandos, en el orden en que se usan, con la consola y la carpeta desde la que se ejecutan. La
ruta base del laboratorio es `E:\vertex-forensic-lab`.

## 1. Comprobar la máquina antes de empezar

**Consola:** PowerShell normal · **Carpeta:** cualquiera

```powershell
# Interfaz de WSL (modo NAT) y su subred
Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.InterfaceAlias -like "*WSL*" }

# Puertos del gateway (8000), del panel (4200) y de LM Studio (1234)
Get-NetTCPConnection -State Listen | Where-Object { $_.LocalPort -in 8000,4200,1234 }

# Reglas de pruebas anteriores
Get-NetFirewallRule | Where-Object { $_.DisplayName -like "VERTEX*" } |
    Select-Object DisplayName, Direction, Action, Enabled
```

## 2. Arrancar el laboratorio

**Consola:** PowerShell **como Administrador** · **Carpeta:** `E:\vertex-forensic-lab`

```powershell
powershell -ExecutionPolicy Bypass -File .\Start-VertexLab.ps1
```

El script genera `.env` la primera vez, crea la regla `VERTEX_LAB_INGRESS_8000` para la subred de WSL,
arranca el gateway en `0.0.0.0:8000` y el panel en `4200`, y abre `http://localhost:4200`.

Comprueba en su salida:

- `Privilegios de Administrador : ACTIVOS`
- `Red WSL (NAT) : 172.x.x.x/20`
- `Regla VERTEX_LAB_INGRESS_8000 : TCP 8000 permitido SOLO desde ...`

## 3. Atacar desde Parrot

**Consola:** terminal de Parrot (WSL) · **Carpeta:** cualquiera

```bash
tr -d '\r' < /mnt/e/vertex-forensic-lab/tmp/swarm_assault.sh > /tmp/swarm_assault.sh
bash /tmp/swarm_assault.sh
```

Repite el `tr` cada vez que cambies el script en Windows.

## 4. Peritar

Desde el panel: botón **EJECUTAR PERITO LLM**. Peritará las sesiones nuevas y las que tengan actividad
desde su último veredicto.

Para re-evaluar todas las sesiones desde la línea de comandos:

**Consola:** PowerShell normal · **Carpeta:** `E:\vertex-forensic-lab`

```powershell
python forensic_coroner_llm.py --rejudge
```

Si DuckDB devuelve un error de archivo en uso, coincidió con un refresco del panel: vuelve a lanzarlo.

Para revisar los veredictos guardados:

```powershell
python inspect_verdicts.py
```

## 5. Aislar al atacante

Desde el panel: botón **AISLAR HOST** en la tarjeta de la sesión. Para comprobar la regla:

**Consola:** PowerShell normal · **Carpeta:** cualquiera

```powershell
Get-NetFirewallRule -DisplayName "VERTEX_BLOCK_*" | Select-Object DisplayName, Enabled
```

Y para confirmar desde Parrot que ya no hay respuesta, vuelve a lanzar `bash /tmp/swarm_assault.sh`.

## 6. Exportar y verificar el acta

Desde el panel: botón **EXPORTAR ACTA SHA-256**. El acta queda en `reports/`.

**Consola:** PowerShell normal · **Carpeta:** `E:\vertex-forensic-lab\reports`

```powershell
Get-FileHash .\ACTA_FORENSE_VERTEX_<fecha>.md -Algorithm SHA256
Get-Content .\ACTA_FORENSE_VERTEX_<fecha>.md.sha256
```

Informe con hash encadenado y sello de la bóveda:

**Consola:** PowerShell normal · **Carpeta:** `E:\vertex-forensic-lab`

```powershell
python forensic_report_compiler.py
```

## 7. Probar el servidor MCP

**Consola:** PowerShell normal (Administrador si quieres bloqueos reales) · **Carpeta:**
`E:\vertex-forensic-lab\vertex-forensic-mcp`

```powershell
python client_test.py
```

## 8. Parar y limpiar

**Consola:** PowerShell **como Administrador** · **Carpeta:** `E:\vertex-forensic-lab`

```powershell
# Solo parar el gateway y el panel (las reglas de bloqueo se mantienen)
powershell -ExecutionPolicy Bypass -File .\Stop-VertexLab.ps1

# Parar y quitar las reglas de bloqueo del SOAR
powershell -ExecutionPolicy Bypass -File .\Stop-VertexLab.ps1 -RemoveBlocks

# Parar y quitar también la regla de entrada de WSL
powershell -ExecutionPolicy Bypass -File .\Stop-VertexLab.ps1 -RemoveBlocks -RemoveIngress
```

Reiniciar el gateway pone a cero el puntaje del tarpit.

## 9. Empaquetar un release

**Consola:** PowerShell normal · **Carpeta:** `E:\vertex-forensic-lab`

```powershell
powershell -ExecutionPolicy Bypass -File .\Invoke-VertexRelease.ps1
```

Deja el zip y su `.sha256` en `C:\VertexBackups`, sin `node_modules`, entornos virtuales, actas ni `.env`.

## 10. Docker (sin probar en este libro)

**Consola:** PowerShell normal · **Carpeta:** `E:\vertex-forensic-lab`

```powershell
docker compose up -d --build
docker compose --profile attack up agent-simulator
```

Requiere `.env` con `VERTEX_CANARY_SECRET`. Dentro del contenedor no hay `netsh`: los bloqueos quedan
como `LOGICAL_BLOCK_ONLY`.
