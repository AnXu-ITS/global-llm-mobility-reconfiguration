param([Parameter(Mandatory=$true)][string]$Config)
$root   = Split-Path -Parent $PSScriptRoot
$bundle = Join-Path $root "ITSAC_REPRO_BUNDLE"
$sumoBin = Join-Path $root ".venv\Lib\site-packages\sumo\bin"
$venvPy  = Join-Path $root ".venv\Scripts\python.exe"
$tool    = Join-Path $bundle "tools\run_revision_v3.py"
$cfg     = Join-Path $bundle "configs\revision_v3\$Config"
$log     = Join-Path $PSScriptRoot ("search_" + ($Config -replace '\.json$','') + ".log")

$env:Path = "$sumoBin;" + $env:Path
Remove-Item Env:SUMO_HOME -ErrorAction SilentlyContinue

$line = "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] START $Config"
Add-Content -Path $log -Value $line
Write-Host $line
$output = & $venvPy $tool search --config $cfg --method llm --run 1 2>&1
$code = $LASTEXITCODE
$output | Add-Content -Path $log
Add-Content -Path $log -Value "[exit code: $code]"
if ($code -ne 0) {
    $fail = "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] HALT: $Config exited $code"
    Add-Content -Path $log -Value $fail
    Write-Host $fail
    exit 1
}
Write-Host "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] DONE $Config"
