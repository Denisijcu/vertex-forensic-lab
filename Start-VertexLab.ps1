$ErrorActionPreference = "Stop"

$LabRoot     = "E:\vertex-forensic-lab"
$BackendDir  = Join-Path $LabRoot "backend"
$FrontendDir = Join-Path $LabRoot "frontend"
$VaultPath   = Join-Path $LabRoot "forensic_vault\telemetry.duckdb"
$EnvFile     = Join-Path $LabRoot ".env"
$IngressRule = "VERTEX_LAB_INGRESS_8000"

Write-Host "==================================================================" -ForegroundColor Cyan
Write-Host "   // VERTEX FORENSIC LAB v1.3 - COMMAND CENTER ORCHESTRATOR      " -ForegroundColor Green
Write-Host "==================================================================" -ForegroundColor Cyan

# ---------------------------------------------------------------
# 1. Secretos (.env) - se generan una sola vez, nunca van a git
# ---------------------------------------------------------------
if (-not (Test-Path $EnvFile)) {
    $bytes = New-Object byte[] 32
    [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
    $secret = -join ($bytes | ForEach-Object { $_.ToString("x2") })
    @(
        "# Vertex Forensic Lab - secretos locales (NO subir a git)",
        "VERTEX_CANARY_SECRET=$secret",
        "VERTEX_ENTROPY_THRESHOLD=4.5"
    ) | Set-Content -Path $EnvFile -Encoding UTF8
    Write-Host "[+] .env creado con VERTEX_CANARY_SECRET aleatorio" -ForegroundColor Green
} else {
    Write-Host "[+] .env presente" -ForegroundColor Green
}

# ---------------------------------------------------------------
# 2. Privilegios
# ---------------------------------------------------------------
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if ($isAdmin) {
    Write-Host "[+] Privilegios de Administrador : ACTIVOS (Enforcer netsh habilitado)" -ForegroundColor Green
} else {
    Write-Host "[!] Privilegios de Administrador : INACTIVOS (bloqueos quedaran como LOGICAL_BLOCK_ONLY)" -ForegroundColor Yellow
}

# ---------------------------------------------------------------
# 3. Subred WSL (modo NAT) y regla de entrada acotada a esa subred
# ---------------------------------------------------------------
$wslIf = Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue | Where-Object { $_.InterfaceAlias -like "vEthernet (WSL*" } | Select-Object -First 1
if ($wslIf) {
    $ipBytes = ([System.Net.IPAddress]::Parse($wslIf.IPAddress)).GetAddressBytes()
    [Array]::Reverse($ipBytes)
    $ipInt   = [BitConverter]::ToUInt32($ipBytes, 0)
    $maskInt = [uint32]([math]::Pow(2, 32) - [math]::Pow(2, 32 - $wslIf.PrefixLength))
    $netBytes = [BitConverter]::GetBytes([uint32]($ipInt -band $maskInt))
    [Array]::Reverse($netBytes)
    $WslSubnet = "{0}/{1}" -f ([System.Net.IPAddress]::new($netBytes)).ToString(), $wslIf.PrefixLength
    Write-Host "[+] Red WSL (NAT)                : $WslSubnet  (host Windows = $($wslIf.IPAddress))" -ForegroundColor Green

    if ($isAdmin) {
        Get-NetFirewallRule -DisplayName $IngressRule -ErrorAction SilentlyContinue | Remove-NetFirewallRule
        New-NetFirewallRule -DisplayName $IngressRule -Direction Inbound -Action Allow -Protocol TCP `
            -LocalPort 8000 -RemoteAddress $WslSubnet -Profile Any | Out-Null
        Write-Host "[+] Regla $IngressRule        : TCP 8000 permitido SOLO desde $WslSubnet" -ForegroundColor Green
    }
} else {
    Write-Host "[!] No se detecto vEthernet (WSL): si WSL usa networking=mirrored, Parrot llegara por 127.0.0.1" -ForegroundColor Yellow
}

# ---------------------------------------------------------------
# 4. Servicios
# ---------------------------------------------------------------
function Test-LocalPort {
    param([int]$Port)
    $conn = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    return ($null -ne $conn)
}

if (Test-LocalPort -Port 1234) {
    Write-Host "[+] Motor Cognitivo LM Studio    : ONLINE (Puerto 1234)" -ForegroundColor Green
} else {
    Write-Host "[!] Motor Cognitivo LM Studio    : OFFLINE (el perito usara dictamen determinista)" -ForegroundColor Yellow
}

if (Test-LocalPort -Port 8000) {
    Write-Host "[!] Puerto 8000 YA OCUPADO: ejecuta Stop-VertexLab.ps1 si quieres reiniciar el gateway con este script" -ForegroundColor Yellow
} else {
    Write-Host "[*] Iniciando FastAPI Forensic Gateway en 0.0.0.0:8000..." -ForegroundColor Cyan
    Start-Process powershell -ArgumentList "-ExecutionPolicy", "Bypass", "-NoExit", "-Command", "`$Host.UI.RawUI.WindowTitle = 'VERTEX GATEWAY (FastAPI :8000)'; Set-Location '$BackendDir'; `$env:DB_PATH='$VaultPath'; python -m uvicorn main:app --host 0.0.0.0 --port 8000"
}

if (Test-LocalPort -Port 4200) {
    Write-Host "[+] Angular 19 Tactical HUD      : YA ACTIVO en http://localhost:4200" -ForegroundColor Green
} else {
    Write-Host "[*] Iniciando Angular 19 Tactical HUD en puerto 4200..." -ForegroundColor Cyan
    Start-Process powershell -ArgumentList "-ExecutionPolicy", "Bypass", "-NoExit", "-Command", "`$Host.UI.RawUI.WindowTitle = 'VERTEX HUD (Angular :4200)'; Set-Location '$FrontendDir'; ng serve --port 4200"
}

Write-Host "[*] Esperando al HUD..." -ForegroundColor Cyan
$retries = 0
while (-not (Test-LocalPort -Port 4200) -and $retries -lt 30) {
    Start-Sleep -Seconds 1
    $retries++
}

Start-Process "http://localhost:4200"
Write-Host "[+] Vertex Forensic Lab v1.3 desplegado." -ForegroundColor Green
Write-Host "==================================================================" -ForegroundColor Cyan
