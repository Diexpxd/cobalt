# Ejecuta las pruebas de Python y las de Java. Devuelve 0 solo si todo pasa.
# Uso: powershell -NoProfile -File cerebro\validar_todo.ps1   (necesita JDK 17 en JAVA_HOME o en el PATH)
$ErrorActionPreference = 'Continue'
$cerebro = $PSScriptRoot
$mod = Join-Path (Split-Path -Parent $cerebro) 'mod'
$py = if ($env:COBALT_PY) { $env:COBALT_PY } else { 'python' }
$global:todoOk = $true

function Paso([string]$nombre, [bool]$paso) {
    Write-Host ("[{0}] {1}" -f $(if ($paso) { 'OK   ' } else { 'FALLA' }), $nombre)
    if (-not $paso) { $global:todoOk = $false }
}

& $py -m py_compile (Join-Path $cerebro 'cerebro\cerebro.py')
Paso 'Python: py_compile cerebro.py' ($LASTEXITCODE -eq 0)
$salida = & $py (Join-Path $cerebro 'tests\run_all.py') 2>&1 | Out-String
$codigoPy = $LASTEXITCODE
Paso 'Python: tests/run_all.py' ($codigoPy -eq 0)
if ($codigoPy -ne 0) {
    ($salida -split "`n") | Where-Object { $_ -cmatch '^FAIL|^Traceback|Error:|FALLAN' } | Select-Object -First 20 | ForEach-Object { Write-Host "      $_" }
}

Push-Location $mod
$gradle = cmd /c ".\gradlew.bat build --console=plain 2>&1" | Out-String
$codigoGradle = $LASTEXITCODE
Pop-Location
Paso 'Java: gradlew build' ($codigoGradle -eq 0)
if ($codigoGradle -eq 0) {
    $pj = & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $mod 'tools\pruebas\ejecutar.ps1') 2>&1 | Out-String
    Paso 'Java: tools/pruebas/ejecutar.ps1' ($LASTEXITCODE -eq 0)

    Push-Location $mod
    $gt = cmd /c ".\gradlew.bat runGameTestServer --console=plain 2>&1" | Out-String
    $codigoGt = $LASTEXITCODE
    Pop-Location
    Paso 'Java: GameTests (servidor sin ventana)' (($codigoGt -eq 0) -and ($gt -match 'All \d+ required tests passed'))
}

if ($global:todoOk) { Write-Host "`nVALIDACION COMPLETA: TODO OK"; exit 0 } else { Write-Host "`nVALIDACION FALLIDA"; exit 1 }
