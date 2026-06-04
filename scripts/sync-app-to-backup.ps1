# Copia código do app (git) para app_local_backup (build EAS / Expo local)
$Root = Split-Path -Parent $PSScriptRoot
$Src = Join-Path $Root "app"
$Dst = Join-Path $Root "app_local_backup"

foreach ($dir in @("app", "src")) {
  $from = Join-Path $Src $dir
  $to = Join-Path $Dst $dir
  if (-not (Test-Path $from)) { continue }
  New-Item -ItemType Directory -Force -Path $to | Out-Null
  robocopy $from $to /E /XD node_modules .expo .git /XF .env /NFL /NDL /NJH /NJS /nc /ns /np
  if ($LASTEXITCODE -ge 8) { exit 1 }
}

foreach ($file in @("app.config.ts", "babel.config.js", "metro.config.js", "tsconfig.json", "package.json")) {
  $f = Join-Path $Src $file
  if (Test-Path $f) { Copy-Item -Force $f (Join-Path $Dst $file) }
}

Write-Host "OK: app -> app_local_backup sincronizado." -ForegroundColor Green
