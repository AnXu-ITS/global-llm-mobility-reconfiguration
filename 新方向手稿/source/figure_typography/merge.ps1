$ErrorActionPreference='Stop'
$work=Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$app=New-Object -ComObject PowerPoint.Application
try {
 $old=$app.Presentations.Open((Join-Path $work 'archive/figures_before_reference_redesign/editable_figures/Figures2_to_8_revised.pptx'),$true,$false,$false)
 try {$old.Slides.Item(3).Export((Join-Path $PSScriptRoot 'figure4_reference.png'),'PNG',1600,900)} finally {$old.Close()}
 $deck=$app.Presentations.Open((Join-Path $work 'archive/figures_before_times_revision/Figures2_to_8_revised.pptx'),$true,$false,$false)
 try {
  $deck.Slides.Item(2).Delete()
  $null=$deck.Slides.InsertFromFile((Join-Path $PSScriptRoot 'output/bar.pptx'),1,1,1)
  $deck.Slides.Item(3).Delete()
  $null=$deck.Slides.InsertFromFile((Join-Path $work 'archive/figures_before_reference_redesign/editable_figures/Figures2_to_8_revised.pptx'),2,3,3)
  $deck.SaveAs((Join-Path $PSScriptRoot 'merged.candidate.pptx'),24)
 } finally {$deck.Close()}
} finally {[Runtime.InteropServices.Marshal]::ReleaseComObject($app)|Out-Null}
