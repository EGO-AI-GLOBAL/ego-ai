# Inicia o painel Streamlit (app.py) na pasta correta do projeto.
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
Write-Host "Pasta: $root"
Write-Host "UI build esperado: 2026-05-20-menu-claro-v2"
Write-Host "URL: http://localhost:8501"
Write-Host ""
python -m streamlit run app.py --server.port 8501
