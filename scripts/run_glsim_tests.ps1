$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$GlsimLauncher = Join-Path $ProjectRoot "scripts\glsim_launcher.py"
$Gltest = Join-Path $ProjectRoot ".venv\Scripts\gltest.exe"
$Stdout = Join-Path $env:TEMP "schemacrosswalk-glsim.stdout.log"
$Stderr = Join-Path $env:TEMP "schemacrosswalk-glsim.stderr.log"

New-Item -ItemType Directory -Path (Join-Path $ProjectRoot "artifacts") -Force | Out-Null
$Process = Start-Process -FilePath $Python `
    -ArgumentList @($GlsimLauncher, "--port", "4075", "--validators", "5", "--seed", "schemacrosswalk-audit", "--no-browser") `
    -WorkingDirectory $ProjectRoot `
    -RedirectStandardOutput $Stdout `
    -RedirectStandardError $Stderr `
    -WindowStyle Hidden `
    -PassThru

try {
    $Ready = $false
    for ($Attempt = 0; $Attempt -lt 100; $Attempt++) {
        try {
            Invoke-WebRequest -Uri "http://127.0.0.1:4075/api" -Method Post -ContentType "application/json" `
                -Body '{"jsonrpc":"2.0","id":1,"method":"eth_chainId","params":[]}' -UseBasicParsing | Out-Null
            $Ready = $true
            break
        }
        catch {
            Start-Sleep -Milliseconds 100
        }
    }
    if (-not $Ready) {
        throw "GLSim did not become ready on port 4075"
    }

    & $Gltest "tests\integration" -v -s --network localnet
    if ($LASTEXITCODE -ne 0) {
        throw "GLSim integration suite failed with exit code $LASTEXITCODE"
    }
}
finally {
    if (-not $Process.HasExited) {
        Stop-Process -Id $Process.Id -Force
    }
}
