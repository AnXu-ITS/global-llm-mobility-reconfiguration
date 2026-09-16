param([switch]$RunRegression)
$ErrorActionPreference = 'Stop'
$revisionDir = Join-Path $PSScriptRoot 'source/revision_v3'
$revisionScripts = @('inspect_evidence.py','morphology_boundary.py','verify_details.py')
if ($RunRegression) { $revisionScripts += 'run_regression.py' }
$revisionScripts += @('analyze_revision.py','finalize_data.py')
foreach ($revisionScript in $revisionScripts) {
    & python (Join-Path $revisionDir $revisionScript)
    if ($LASTEXITCODE -ne 0) { throw "Failed: $revisionScript" }
}
