$ErrorActionPreference = 'Stop'
Push-Location $PSScriptRoot
try {
    pdflatex -interaction=nonstopmode -halt-on-error -jobname=main_edited main.tex
    if ($LASTEXITCODE -ne 0) { throw 'Main first pass failed' }
    bibtex main_edited
    if ($LASTEXITCODE -ne 0) { throw 'Bibliography failed' }
    pdflatex -interaction=nonstopmode -halt-on-error -jobname=main_edited main.tex
    if ($LASTEXITCODE -ne 0) { throw 'Main second pass failed' }
    pdflatex -interaction=nonstopmode -halt-on-error -jobname=main_edited main.tex
    if ($LASTEXITCODE -ne 0) { throw 'Main final pass failed' }
    pdflatex -interaction=nonstopmode -halt-on-error -jobname=supplement_edited supplement.tex
    if ($LASTEXITCODE -ne 0) { throw 'Supplement first pass failed' }
    pdflatex -interaction=nonstopmode -halt-on-error -jobname=supplement_edited supplement.tex
    if ($LASTEXITCODE -ne 0) { throw 'Supplement final pass failed' }
} finally { Pop-Location }
