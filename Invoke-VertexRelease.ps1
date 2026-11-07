$ErrorActionPreference = "Stop"

$SourceDir = "E:\vertex-forensic-lab"
$BackupDir = "C:\VertexBackups"
$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$ReleaseName = "Vertex-Forensic-Lab_v1.3_$Timestamp"
$StagingDir = Join-Path $env:TEMP $ReleaseName
$ZipPath = Join-Path $BackupDir "$ReleaseName.zip"

Write-Host "[*] Iniciando empaquetado de release: $ReleaseName" -ForegroundColor Cyan

# 1. Asegurar directorio de backups
if (-not (Test-Path $BackupDir)) {
    New-Item -ItemType Directory -Path $BackupDir | Out-Null
}

# 2. Copiar código fuente excluyendo artefactos de compilación y entornos pesados
# '.env' también se excluye: contiene VERTEX_CANARY_SECRET
$ExcludeDirs = @("node_modules", ".angular", ".venv", "venv", "__pycache__", ".git", "dist", "reports", ".env")
New-Item -ItemType Directory -Path $StagingDir -Force | Out-Null

Get-ChildItem -Path $SourceDir -Recurse | Where-Object {
    $item = $_
    $relPath = $item.FullName.Substring($SourceDir.Length + 1)
    $parts = $relPath -split '[\\/]'
    ($parts | Where-Object { $ExcludeDirs -contains $_ }).Count -eq 0
} | ForEach-Object {
    $targetPath = Join-Path $StagingDir $_.FullName.Substring($SourceDir.Length + 1)
    if ($_.PSIsContainer) {
        if (-not (Test-Path $targetPath)) {
            New-Item -ItemType Directory -Path $targetPath -Force | Out-Null
        }
    } else {
        $parentDir = Split-Path $targetPath -Parent
        if (-not (Test-Path $parentDir)) {
            New-Item -ItemType Directory -Path $parentDir -Force | Out-Null
        }
        Copy-Item -Path $_.FullName -Destination $targetPath -Force
    }
}

# 3. Comprimir y firmar con SHA-256
Compress-Archive -Path "$StagingDir\*" -DestinationPath $ZipPath -Force
Remove-Item -Path $StagingDir -Recurse -Force

$FileHash = (Get-FileHash -Path $ZipPath -Algorithm SHA256).Hash
$HashFile = "$ZipPath.sha256"
"$FileHash  $ReleaseName.zip" | Set-Content -Path $HashFile -Encoding UTF8

Write-Host "[+] Paquete generado : $ZipPath" -ForegroundColor Green
Write-Host "[+] Firma SHA-256    : $FileHash" -ForegroundColor Yellow