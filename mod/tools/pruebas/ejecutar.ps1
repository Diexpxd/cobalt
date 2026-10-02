# Ejecuta las pruebas de Java SIN abrir Minecraft: compila con Gradle y corre cada *.java de esta carpeta
# (archivo de un solo fuente) con ítems y bloques reales de Minecraft. Uso:  .\tools\pruebas\ejecutar.ps1
param([string]$Solo = '')   # opcional: solo los archivos cuyo nombre contenga este texto (p. ej. -Solo Bloques)
$ErrorActionPreference = 'Stop'
$raiz = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)   # tools/pruebas -> mod
Push-Location $raiz
try {
    & .\gradlew.bat compileJava --console=plain | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "compileJava falló: no se ejecutan las pruebas" }
} finally { Pop-Location }

$g = Join-Path $env:USERPROFILE '.gradle\caches'
$forge = Get-ChildItem (Join-Path $g 'forge_gradle\minecraft_user_repo\net\minecraftforge\forge') -Recurse -Filter 'forge-*_mapped_official_*.jar' |
         Where-Object { $_.Name -notmatch 'sources|recomp' } | Select-Object -First 1
$extra = Join-Path $g 'forge_gradle\minecraft_repo\versions\1.20.1\client-extra.jar'
$gecko = Get-ChildItem (Join-Path $g 'forge_gradle\deobf_dependencies\software\bernie\geckolib') -Recurse -Filter 'geckolib-forge-1.20.1-4.4.9_mapped_official_1.20.1.jar' | Select-Object -First 1
# Librerías de Minecraft/Forge; se descartan las versiones antiguas duplicadas (mezclarlas rompe fastutil, gson...)
$viejas = 'fastutil-8\.3\.1|gson-2\.9\.1|gson-2\.10\.jar|commons-lang3-3\.9\.jar|commons-codec-1\.11|slf4j-api-1\.7\.30|commons-compress-1\.18'
$libs = Get-ChildItem (Join-Path $g 'modules-2\files-2.1') -Recurse -Filter '*.jar' |
        Where-Object { $_.Name -notmatch 'sources|natives|javadoc' -and $_.Name -notmatch $viejas }
$clases = Join-Path $raiz 'build\classes\java\main'
$cp = (@($clases, $forge.FullName, $extra, $gecko.FullName) + ($libs | ForEach-Object { $_.FullName })) -join ';'

# Minecraft crea 'logs/latest.log' en el directorio de trabajo: se ejecuta desde una carpeta temporal para no ensuciar el proyecto
$trabajo = Join-Path $env:TEMP 'cobalt_pruebas_java'
New-Item -ItemType Directory -Force $trabajo | Out-Null
$fallos = 0
Push-Location $trabajo
try {
    foreach ($prueba in Get-ChildItem $PSScriptRoot -Filter '*.java' | Where-Object { -not $Solo -or $_.Name -like "*$Solo*" }) {
        Write-Host "`n===== $($prueba.Name) =====" -ForegroundColor Cyan
        $salida = & java -cp $cp $prueba.FullName 2>&1 | Where-Object { $_ -notmatch 'SLF4J|StaticLoggerBinder|Failed to load class|^Note:' }
        $salida | ForEach-Object { Write-Host $_ }
        if ($LASTEXITCODE -ne 0) { $fallos++ }
    }
} finally { Pop-Location }
if ($fallos -eq 0) { Write-Host "`nTODAS LAS PRUEBAS DE JAVA OK" -ForegroundColor Green } else { Write-Host "`nFALLAN $fallos ARCHIVO(S)" -ForegroundColor Red; exit 1 }
