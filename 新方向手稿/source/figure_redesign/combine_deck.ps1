param([string]$TaskRoot)
$ErrorActionPreference='Stop'
$work=(Resolve-Path -LiteralPath $TaskRoot).Path
$out=Join-Path $work 'source/figure_redesign'
$original=Join-Path $work 'overleaf/editable_figures/Figures2_to_8_revised.pptx'
$new=Join-Path $out 'output/figures3_to_8_v4_r5.pptx'
$app=New-Object -ComObject PowerPoint.Application
$initialCount=$app.Presentations.Count
try {
 $deck=$app.Presentations.Open($original,$true,$false,$false)
 try {
  $deck.Slides.Item(1).Export((Join-Path $out 'figure2_before.png'),'PNG',1840,1035)
  $countBefore=$deck.Slides.Item(1).Shapes.Count
  for($i=$deck.Slides.Count;$i -ge 2;$i--){$deck.Slides.Item($i).Delete()}
  $n=$deck.Slides.InsertFromFile($new,1,1,6)
  if($n -ne 6 -or $deck.Slides.Count -ne 7){throw 'Unexpected merged slide count'}
  if($deck.Slides.Item(1).Shapes.Count -ne $countBefore){throw 'Figure 2 shape count changed'}
  $deck.Slides.Item(1).Export((Join-Path $out 'figure2_after.png'),'PNG',1840,1035)
  $deck.SaveAs((Join-Path $out 'output/Figures2_to_8_reference_redesign.pptx'),24)
  $deck.SaveAs((Join-Path $out 'combined.pdf'),32)
 } finally {$deck.Close()}
} finally {
 if($initialCount -eq 0 -and $app.Presentations.Count -eq 0){$app.Quit()}
 [Runtime.InteropServices.Marshal]::ReleaseComObject($app)|Out-Null
}
Write-Output 'Seven-slide deck merged; Figure 2 retained from the original.'
