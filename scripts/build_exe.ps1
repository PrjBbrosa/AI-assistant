[CmdletBinding()]
param(
    [string]$Version = "",
    [string]$PythonExe = "",
    [string]$AppName = "LocalEngineeringAssistant",
    [string]$EntryScript = "app/main.py",
    [string]$OutputRoot = "dist/releases",
    [string]$BuildRoot = "build/pyinstaller",
    [switch]$OneFile,
    [switch]$SkipInstall,
    [switch]$NoClean,
    [switch]$Zip
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$script:ProjectRoot = Split-Path -Parent $PSScriptRoot

function Write-Step {
    param([Parameter(Mandatory = $true)][string]$Message)
    Write-Host "[build] $Message"
}

function Resolve-ProjectPath {
    param(
        [Parameter(Mandatory = $true)][string]$PathValue,
        [switch]$AllowMissing
    )

    $fullPath = if ([System.IO.Path]::IsPathRooted($PathValue)) {
        [System.IO.Path]::GetFullPath($PathValue)
    } else {
        [System.IO.Path]::GetFullPath((Join-Path $script:ProjectRoot $PathValue))
    }

    if (-not $AllowMissing -and -not (Test-Path -LiteralPath $fullPath)) {
        throw "Path not found: $fullPath"
    }

    return $fullPath
}

function Resolve-PythonCommand {
    param([string]$PreferredPath)

    if (-not [string]::IsNullOrWhiteSpace($PreferredPath)) {
        $resolvedPreferred = Resolve-ProjectPath -PathValue $PreferredPath
        return @{
            Command    = $resolvedPreferred
            PrefixArgs = @()
            Display    = $resolvedPreferred
        }
    }

    $venvPython = Resolve-ProjectPath -PathValue ".venv\Scripts\python.exe" -AllowMissing
    if (Test-Path -LiteralPath $venvPython) {
        return @{
            Command    = $venvPython
            PrefixArgs = @()
            Display    = $venvPython
        }
    }

    $python = Get-Command python -ErrorAction SilentlyContinue
    if ($null -ne $python) {
        return @{
            Command    = $python.Source
            PrefixArgs = @()
            Display    = $python.Source
        }
    }

    $pyLauncher = Get-Command py -ErrorAction SilentlyContinue
    if ($null -ne $pyLauncher) {
        return @{
            Command    = $pyLauncher.Source
            PrefixArgs = @("-3")
            Display    = "$($pyLauncher.Source) -3"
        }
    }

    throw "No Python interpreter found. Pass -PythonExe or create .venv\Scripts\python.exe."
}

function Invoke-Python {
    param([Parameter(Mandatory = $true)][string[]]$Arguments)

    & $script:PythonCommand @script:PythonPrefixArgs @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Python command failed with exit code $LASTEXITCODE."
    }
}

function Get-PythonOutput {
    param([Parameter(Mandatory = $true)][string[]]$Arguments)

    $output = & $script:PythonCommand @script:PythonPrefixArgs @Arguments 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "Python command failed with exit code $LASTEXITCODE."
    }

    return ($output | Out-String).Trim()
}

function Convert-ToWindowsVersionParts {
    param([Parameter(Mandatory = $true)][string]$VersionText)

    $parts = New-Object System.Collections.Generic.List[int]
    foreach ($match in [regex]::Matches($VersionText, "\d+")) {
        if ($parts.Count -ge 4) {
            break
        }
        $parts.Add([int]$match.Value)
    }

    while ($parts.Count -lt 4) {
        $parts.Add(0)
    }

    return ,$parts.ToArray()
}

function New-PyInstallerVersionFile {
    param(
        [Parameter(Mandatory = $true)][string]$FilePath,
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][string]$VersionText
    )

    $versionParts = Convert-ToWindowsVersionParts -VersionText $VersionText
    $versionTuple = "$($versionParts[0]), $($versionParts[1]), $($versionParts[2]), $($versionParts[3])"
    $content = @"
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=($versionTuple),
    prodvers=($versionTuple),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo(
      [
        StringTable(
          '040904B0',
          [
            StringStruct('CompanyName', 'Personal'),
            StringStruct('FileDescription', '$Name'),
            StringStruct('FileVersion', '$VersionText'),
            StringStruct('InternalName', '$Name'),
            StringStruct('OriginalFilename', '$Name.exe'),
            StringStruct('ProductName', '$Name'),
            StringStruct('ProductVersion', '$VersionText')
          ]
        )
      ]
    ),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
"@

    Set-Content -LiteralPath $FilePath -Value $content -Encoding UTF8
}

function Get-GitText {
    param([Parameter(Mandatory = $true)][string[]]$Arguments)

    $gitCommand = Get-Command git -ErrorAction SilentlyContinue
    if ($null -eq $gitCommand) {
        return ""
    }

    $output = & $gitCommand.Source -C $script:ProjectRoot @Arguments 2>$null
    if ($LASTEXITCODE -ne 0) {
        return ""
    }

    return ($output | Out-String).Trim()
}

if ([string]::IsNullOrWhiteSpace($Version)) {
    $Version = Get-Date -Format "yyyy.MM.dd.0"
}

$pythonConfig = Resolve-PythonCommand -PreferredPath $PythonExe
$script:PythonCommand = $pythonConfig.Command
$script:PythonPrefixArgs = @($pythonConfig.PrefixArgs)

$entryScriptPath = Resolve-ProjectPath -PathValue $EntryScript
$iconPath = Resolve-ProjectPath -PathValue "app/assets/assistant_icon.ico" -AllowMissing
$releaseRoot = Resolve-ProjectPath -PathValue $OutputRoot -AllowMissing
$buildRootPath = Resolve-ProjectPath -PathValue $BuildRoot -AllowMissing
$versionOutputRoot = Join-Path $releaseRoot $Version
$workPath = Join-Path $buildRootPath $Version
$specPath = Join-Path $workPath "spec"
$versionFilePath = Join-Path $workPath "windows-version-info.txt"

if (-not $NoClean) {
    Write-Step "Cleaning previous artifacts for version $Version"
    Remove-Item -LiteralPath $versionOutputRoot -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $workPath -Recurse -Force -ErrorAction SilentlyContinue
}

New-Item -ItemType Directory -Force -Path $versionOutputRoot | Out-Null
New-Item -ItemType Directory -Force -Path $workPath | Out-Null
New-Item -ItemType Directory -Force -Path $specPath | Out-Null

New-PyInstallerVersionFile -FilePath $versionFilePath -Name $AppName -VersionText $Version

Write-Step "Using Python: $($pythonConfig.Display)"
Write-Step "Building version: $Version"

if (-not $SkipInstall) {
    Write-Step "Installing dependencies from requirements.txt"
    Invoke-Python -Arguments @("-m", "pip", "install", "-r", (Resolve-ProjectPath -PathValue "requirements.txt"))
}

$pyInstallerArgs = @(
    "-m", "PyInstaller",
    "--noconfirm",
    "--windowed",
    "--name", $AppName,
    "--paths", $script:ProjectRoot,
    "--distpath", $versionOutputRoot,
    "--workpath", $workPath,
    "--specpath", $specPath,
    "--version-file", $versionFilePath
)

if (-not $NoClean) {
    $pyInstallerArgs += "--clean"
}

if ($OneFile) {
    $pyInstallerArgs += "--onefile"
} else {
    $pyInstallerArgs += "--onedir"
}

if (Test-Path -LiteralPath $iconPath) {
    $pyInstallerArgs += @("--icon", $iconPath)
}

$dataMappings = @(
    @{ Source = "app/assets"; Target = "app/assets" },
    @{ Source = "examples"; Target = "examples" },
    @{ Source = "docs"; Target = "docs" }
)

foreach ($mapping in $dataMappings) {
    $sourcePath = Resolve-ProjectPath -PathValue $mapping.Source -AllowMissing
    if (Test-Path -LiteralPath $sourcePath) {
        $pyInstallerArgs += @("--add-data", "$sourcePath;$($mapping.Target)")
    }
}

$pyInstallerArgs += $entryScriptPath

Write-Step "Running PyInstaller"
Invoke-Python -Arguments $pyInstallerArgs

$artifactPath = if ($OneFile) {
    Join-Path $versionOutputRoot "$AppName.exe"
} else {
    Join-Path $versionOutputRoot $AppName
}

if (-not (Test-Path -LiteralPath $artifactPath)) {
    throw "Build completed but artifact was not found: $artifactPath"
}

$pythonVersion = Get-PythonOutput -Arguments @("--version")
$gitCommit = Get-GitText -Arguments @("rev-parse", "--short", "HEAD")
$gitStatus = Get-GitText -Arguments @("status", "--porcelain")
$metadata = [ordered]@{
    app_name    = $AppName
    version     = $Version
    build_mode  = if ($OneFile) { "onefile" } else { "onedir" }
    artifact    = $artifactPath
    built_at    = (Get-Date).ToString("yyyy-MM-ddTHH:mm:ssK")
    python      = $pythonVersion
    git_commit  = $gitCommit
    git_dirty   = -not [string]::IsNullOrWhiteSpace($gitStatus)
}

$metadataPath = if ($OneFile) {
    Join-Path $versionOutputRoot "build-info.json"
} else {
    Join-Path $artifactPath "build-info.json"
}
$metadata | ConvertTo-Json | Set-Content -LiteralPath $metadataPath -Encoding UTF8

if ($Zip) {
    $zipPath = Join-Path $versionOutputRoot "$AppName-$Version.zip"
    if (Test-Path -LiteralPath $zipPath) {
        Remove-Item -LiteralPath $zipPath -Force
    }

    Write-Step "Creating release archive"
    Compress-Archive -Path $artifactPath -DestinationPath $zipPath -Force
}

Write-Step "Build completed: $artifactPath"
