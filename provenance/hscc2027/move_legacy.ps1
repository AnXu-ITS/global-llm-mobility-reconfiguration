$ErrorActionPreference = 'Stop'
$taskRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$manifest = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'legacy_freeze_manifest.json') -Raw | ConvertFrom-Json
if (-not $manifest.backup_full_hash_verification) { throw 'Verified backup required before moving.' }
$legacyTarget = [IO.Path]::GetFullPath((Join-Path $taskRoot $manifest.archive_root))
if (-not $legacyTarget.StartsWith($taskRoot + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) { throw 'Archive target outside workspace.' }
if (Test-Path -LiteralPath $legacyTarget) { throw 'Archive destination already exists; inspect before resuming.' }
$moves = @()
foreach ($name in $manifest.names) {
    $source = (Resolve-Path -LiteralPath (Join-Path $taskRoot $name)).Path
    $destination = [IO.Path]::GetFullPath((Join-Path $legacyTarget $name))
    if (-not $source.StartsWith($taskRoot + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) { throw "Invalid source: $source" }
    if (-not $destination.StartsWith($legacyTarget + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) { throw "Invalid destination: $destination" }
    $moves += [PSCustomObject]@{ source=$source; destination=$destination; name=$name }
}
$moves | ConvertTo-Json -Depth 3 | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'move_plan.json') -Encoding utf8
New-Item -ItemType Directory -Path $legacyTarget | Out-Null
# Keep the original Git metadata with its original worktree; do not merge histories.
foreach ($move in ($moves | Sort-Object @{Expression={ $_.name -eq '.git' }})) {
    Move-Item -LiteralPath $move.source -Destination $move.destination -Force
    [PSCustomObject]@{ name=$move.name; completed=(Get-Date).ToString('o') } | ConvertTo-Json -Compress | Add-Content -LiteralPath (Join-Path $PSScriptRoot 'move_journal.jsonl') -Encoding utf8
}
Write-Output "Archived original project at $legacyTarget"
