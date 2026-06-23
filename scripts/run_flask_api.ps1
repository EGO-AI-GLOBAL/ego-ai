# Mata processo na porta 5000 e inicia flask_api.py com o código atual.
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$pids = Get-NetTCPConnection -LocalPort 5000 -ErrorAction SilentlyContinue |
  Select-Object -ExpandProperty OwningProcess -Unique

foreach ($procId in $pids) {
  if ($procId -and $procId -gt 0) {
    Write-Host "A terminar PID $procId na porta 5000..."
    Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 1
  }
}

Write-Host "A iniciar Flask em $root ..."
python flask_api.py
