param(
  [Parameter(Mandatory=$true)][string]$City,
  [Parameter(Mandatory=$true)][string]$Method,
  [int]$StartRun = 1,
  [int]$EndRun = 10
)
$root   = Split-Path -Parent $PSScriptRoot
$bundle = Join-Path $root "ITSAC_REPRO_BUNDLE"
$sumoBin = Join-Path $root ".venv\Lib\site-packages\sumo\bin"
$venvPy  = Join-Path $root ".venv\Scripts\python.exe"
$tool    = Join-Path $bundle "tools\run_revision_v3.py"
$cfgSuffix = $Method
if ($Method -eq "llm_no_feedback") { $cfgSuffix = "llm_nofb" }
$cfg = Join-Path $bundle "configs\revision_v3\${City}_search_v1_${cfgSuffix}.json"
$log = Join-Path $PSScriptRoot "search_${City}_${Method}.log"

$env:Path = "$sumoBin;" + $env:Path
Remove-Item Env:SUMO_HOME -ErrorAction SilentlyContinue

for ($r = $StartRun; $r -le $EndRun; $r++) {
    $line = "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] START $City $Method run $r"
    Add-Content -Path $log -Value $line
    Write-Host $line
    $output = & $venvPy $tool search --config $cfg --method $Method --run $r 2>&1
    $code = $LASTEXITCODE
    $output | Add-Content -Path $log
    Add-Content -Path $log -Value "[exit code: $code]"
    if ($code -ne 0) {
        $fail = "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] HALT: $City $Method run $r exited $code"
        Add-Content -Path $log -Value $fail
        Write-Host $fail
        exit 1
    }
}
Write-Host "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] ALL DONE $City $Method (runs $StartRun..$EndRun)"
