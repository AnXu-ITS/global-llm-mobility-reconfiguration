$ErrorActionPreference='Stop'
$taskRoot=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$legacyRoot=(Resolve-Path -LiteralPath (Join-Path $taskRoot 'legacy/20260918')).Path
$planPath=Join-Path $PSScriptRoot '../outputs/bootstrap/cleanup_plan.json'
$plan=Get-Content -LiteralPath $planPath -Raw | ConvertFrom-Json
if (-not $plan.backup_verified) { throw 'Verified backup required' }
$journal=Join-Path $PSScriptRoot '../outputs/bootstrap/cleanup_journal.jsonl'
foreach ($item in $plan.files) {
    $resolved=(Resolve-Path -LiteralPath $item.path).Path
    if (-not $resolved.StartsWith($legacyRoot+'\',[StringComparison]::OrdinalIgnoreCase)) { throw 'Path outside legacy' }
    if ((Get-Item -LiteralPath $resolved -Force).PSIsContainer) { throw 'Only explicitly verified files can be removed' }
    if ((Get-FileHash -LiteralPath $resolved -Algorithm SHA256).Hash -ne $item.sha256) { throw "Changed input: $resolved" }
}
foreach ($item in $plan.files) {
    Remove-Item -LiteralPath $item.path -Force
    $item | ConvertTo-Json -Compress | Add-Content -LiteralPath $journal -Encoding utf8
}
Write-Output "Removed $($plan.files.Count) verified regenerable cache files; backup preserved."
