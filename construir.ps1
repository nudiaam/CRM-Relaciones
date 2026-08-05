param(
    [string]$Python = ""
)

$ErrorActionPreference = "Stop"
$raizProyecto = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $raizProyecto

if (-not $Python) {
    $candidatos = @(
        (Join-Path $raizProyecto "venv\Scripts\python.exe"),
        (Get-Command python -ErrorAction SilentlyContinue).Source,
        (Get-Command py -ErrorAction SilentlyContinue).Source
    ) | Where-Object { $_ -and (Test-Path -LiteralPath $_) }

    foreach ($candidato in $candidatos) {
        try {
            & $candidato -c "import sys; print(sys.executable)" *> $null
            if ($LASTEXITCODE -eq 0) {
                $Python = $candidato
                break
            }
        } catch {
            continue
        }
    }
}

if (-not $Python -or -not (Test-Path -LiteralPath $Python)) {
    throw "No encuentro un Python utilizable. Indícalo con -Python C:\ruta\python.exe"
}

$dependencias = Join-Path $raizProyecto ".paquete-deps"
New-Item -ItemType Directory -Path $dependencias -Force | Out-Null

& $Python -m pip install --disable-pip-version-check --upgrade `
    --target $dependencias -r (Join-Path $raizProyecto "requisitos-paquete.txt")
if ($LASTEXITCODE -ne 0) {
    throw "No se han podido preparar las dependencias del paquete."
}

$pythonPathAnterior = $env:PYTHONPATH
try {
    $env:PYTHONPATH = if ($pythonPathAnterior) {
        "$dependencias;$pythonPathAnterior"
    } else {
        $dependencias
    }
    & $Python -m PyInstaller --noconfirm --clean `
        (Join-Path $raizProyecto "Relaciones.spec")
    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller no ha podido construir Relaciones."
    }
} finally {
    $env:PYTHONPATH = $pythonPathAnterior
}

$construido = Join-Path $raizProyecto "dist\Relaciones.exe"
if (-not (Test-Path -LiteralPath $construido)) {
    throw "La construcción terminó sin crear Relaciones.exe."
}

$resultado = Join-Path $raizProyecto "Relaciones.exe"
Copy-Item -LiteralPath $construido -Destination $resultado -Force
Get-Item -LiteralPath $resultado | Select-Object FullName, Length, LastWriteTime
