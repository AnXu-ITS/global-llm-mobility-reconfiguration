$ErrorActionPreference='Stop'
$taskRoot=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$legacyRoot=(Resolve-Path -LiteralPath (Join-Path $taskRoot 'legacy/20260918')).Path
$plan=Get-Content -LiteralPath (Join-Path $PSScriptRoot '../outputs/bootstrap/cold_storage_plan.json') -Raw -Encoding utf8 | ConvertFrom-Json
if (-not $plan.verified -or $plan.legacy_root -ne $legacyRoot) { throw 'Verified matching plan required' }
if ((Get-FileHash -LiteralPath $plan.backup -Algorithm SHA256).Hash -ne $plan.backup_sha256) { throw 'Backup changed' }
$allowed=@('runs','outputs','tmp','archive/experiment1_v1','archive/experiment3_v1') | ForEach-Object { [IO.Path]::GetFullPath((Join-Path $legacyRoot $_)) }
foreach ($target in $plan.targets) {
    $resolved=(Resolve-Path -LiteralPath $target).Path
    $item=Get-Item -LiteralPath $resolved -Force
    if (-not $resolved.StartsWith($legacyRoot+'\',[StringComparison]::OrdinalIgnoreCase)) { throw 'Outside legacy' }
    if ($resolved -notin $allowed -or -not $item.PSIsContainer) { throw 'Invalid target directory' }
    # OneDrive cloud placeholders also carry ReparsePoint; only actual links redirect paths.
    if ($item.LinkType) { throw 'Refuse directory link' }
}
foreach ($target in $plan.targets) {
    Remove-Item -LiteralPath $target -Recurse -Force
    @{target=$target;status='removed_local_copy';backup=$plan.backup;time=(Get-Date).ToString('o')} | ConvertTo-Json -Compress | Add-Content -LiteralPath (Join-Path $PSScriptRoot '../outputs/bootstrap/cold_storage_journal.jsonl') -Encoding utf8
    Write-Output "Pruned verified local copy: $target"
}
