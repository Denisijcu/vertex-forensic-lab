param(
    # Borra las reglas VERTEX_BLOCK_* / VERTEX_MCP_BLOCK_* creadas por el SOAR (requiere Admin)
    [switch]$RemoveBlocks,
    # Borra la regla de entrada VERTEX_LAB_INGRESS_8000 (requiere Admin)
    [switch]$RemoveIngress
)

$Ports = @(8000, 4200)
foreach ($p in $Ports) {
    $conns = Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue
    foreach ($c in $conns) {
        Write-Host "[*] Deteniendo servicio en puerto $p (PID: $($c.OwningProcess))..." -ForegroundColor Yellow
        Stop-Process -Id $c.OwningProcess -Force -ErrorAction SilentlyContinue
    }
}
Write-Host "[+] Puertos 8000 y 4200 liberados." -ForegroundColor Green

if ($RemoveBlocks -or $RemoveIngress) {
    $isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
    if (-not $isAdmin) {
        Write-Host "[!] Para borrar reglas de firewall abre PowerShell como Administrador." -ForegroundColor Yellow
        return
    }
}

if ($RemoveBlocks) {
    $rules = Get-NetFirewallRule -ErrorAction SilentlyContinue | Where-Object { $_.DisplayName -like "VERTEX_BLOCK_*" -or $_.DisplayName -like "VERTEX_MCP_BLOCK_*" }
    foreach ($r in $rules) {
        Write-Host "[*] Eliminando regla $($r.DisplayName)" -ForegroundColor Yellow
        $r | Remove-NetFirewallRule
    }
    Write-Host "[+] Reglas de bloqueo SOAR eliminadas: $(@($rules).Count)" -ForegroundColor Green
}

if ($RemoveIngress) {
    Get-NetFirewallRule -DisplayName "VERTEX_LAB_INGRESS_8000" -ErrorAction SilentlyContinue | Remove-NetFirewallRule
    Write-Host "[+] Regla VERTEX_LAB_INGRESS_8000 eliminada." -ForegroundColor Green
}
