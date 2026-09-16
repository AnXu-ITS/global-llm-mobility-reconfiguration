param([switch]$ExportFigures)
$ErrorActionPreference='Stop'
$repoRoot=Split-Path -Parent $PSScriptRoot
if ($ExportFigures) {
    $stamp=Get-Date -Format 'yyyyMMdd_HHmmss'
    $backupRoot=Join-Path (Split-Path -Parent $repoRoot) "archive/manual_figures_$stamp"
    New-Item -ItemType Directory -Path $backupRoot -Force | Out-Null
    Copy-Item -LiteralPath (Join-Path $repoRoot 'figures') -Destination $backupRoot -Recurse
    Copy-Item -LiteralPath (Join-Path $repoRoot 'editable_figures') -Destination $backupRoot -Recurse
    $pyCandidate=Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
    $pyRuntime=if (Test-Path -LiteralPath $pyCandidate) {$pyCandidate} else {'python'}
    & $pyRuntime -c 'import pymupdf'
    if ($LASTEXITCODE -ne 0) {throw 'PyMuPDF unavailable; figures have not changed.'}
    $app=New-Object -ComObject PowerPoint.Application
    $initialCount=$app.Presentations.Count
    try {
        foreach($item in @(@('editable_figures/Figure1_revised.pptx','figure1.pdf'),@('archive/figures_pre_editorial_20260914/Figures2_to_8_revised.pptx','figures2_to_8.pdf'))) {
            $deck=$app.Presentations.Open((Join-Path $repoRoot $item[0]),$true,$false,$false)
            try {$deck.SaveAs((Join-Path $backupRoot $item[1]),32)} finally {$deck.Close()}
        }
    } finally {
        if($initialCount -eq 0 -and $app.Presentations.Count -eq 0){$app.Quit()}
        [System.Runtime.InteropServices.Marshal]::ReleaseComObject($app)|Out-Null
    }
    & $pyRuntime (Join-Path $PSScriptRoot 'split_figures.py') $backupRoot
    if($LASTEXITCODE -ne 0){throw 'Figure export failed; inspect the backup directory.'}
    & $pyRuntime (Join-Path $repoRoot 'editable_figures/editorial/source/build_editorial_figures.py')
    if($LASTEXITCODE -ne 0){throw 'Editorial figure generation failed; inspect its alignment reports.'}
    foreach($pair in @(@('Figure2','fig02'),@('Figure3','fig03'),@('Figure4','fig04'),@('Figure5','fig06'),@('Figure6','fig07'),@('FigureS3','figS03'))) {
        Copy-Item -LiteralPath (Join-Path $repoRoot "editable_figures/editorial/output/$($pair[0]).pdf") -Destination (Join-Path $repoRoot "figures/$($pair[1]).pdf") -Force
    }
}
Push-Location $repoRoot
try {
    & pdflatex -interaction=nonstopmode -halt-on-error -jobname=main_revised main.tex
    if($LASTEXITCODE -ne 0){throw 'Main LaTeX build failed'}
    & bibtex main_revised
    if($LASTEXITCODE -ne 0){throw 'BibTeX failed'}
    1..2 | ForEach-Object {
        & pdflatex -interaction=nonstopmode -halt-on-error -jobname=main_revised main.tex
        if($LASTEXITCODE -ne 0){throw 'Main LaTeX build failed'}
        & pdflatex -interaction=nonstopmode -halt-on-error -jobname=supplement_revised supplement.tex
        if($LASTEXITCODE -ne 0){throw 'Supplement build failed'}
    }
} finally {Pop-Location}
Write-Output 'Updated main_revised.pdf and supplement_revised.pdf. Check both PDFs before committing.'
