# Publica a ponte .NET no Autoloader do AutoCAD (por usuario, sem admin).
# Depois de rodar: feche e abra o AutoCAD UMA vez. A ponte sobe junto.
param(
    [string]$AutoCadDir = "C:\Program Files\Autodesk\AutoCAD 2025",
    [switch]$SemBuild
)
$ErrorActionPreference = "Stop"
$raiz = Split-Path -Parent $PSScriptRoot
$dotnet = Join-Path $env:LOCALAPPDATA "Microsoft\dotnet\dotnet.exe"
if (-not (Test-Path $dotnet)) { $dotnet = "dotnet" }

if (-not $SemBuild) {
    Write-Host "compilando..."
    & $dotnet build (Join-Path $PSScriptRoot "CadMcpBridge\CadMcpBridge.csproj") `
        -c Release -v q "-p:AutoCadDir=$AutoCadDir"
    if ($LASTEXITCODE -ne 0) { throw "build falhou (veja a saida acima)" }
}

$bundle = Join-Path $env:APPDATA "Autodesk\ApplicationPlugins\CadMcpBridge.bundle"
$destino = Join-Path $bundle "Contents\Windows"
New-Item -ItemType Directory -Force $destino | Out-Null
Copy-Item (Join-Path $PSScriptRoot "CadMcpBridge\bin\Release\CadMcpBridge.dll") $destino -Force
Copy-Item (Join-Path $PSScriptRoot "CadMcpBridge.bundle\PackageContents.xml") $bundle -Force

Write-Host "instalado em: $bundle"
Write-Host "feche e abra o AutoCAD; a ponte sobe com ele (comando MPCBRIDGE mostra o estado)."
Write-Host "depois: python -m cad_mcp.bridge ping"
