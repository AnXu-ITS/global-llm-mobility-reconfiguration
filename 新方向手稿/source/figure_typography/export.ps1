$ErrorActionPreference='Stop'
$app=New-Object -ComObject PowerPoint.Application
try {
 foreach($item in @(@('Figure1_Times.pptx','figure1'),@('Figures2_to_8_Times_ready.pptx','figures2_to_8'))) {
  $deck=$app.Presentations.Open((Join-Path $PSScriptRoot ('output/'+$item[0])),$true,$false,$false)
  try {
   $deck.SaveAs((Join-Path $PSScriptRoot ($item[1]+'.pdf')),32)
   $height=[int](1600*$deck.PageSetup.SlideHeight/$deck.PageSetup.SlideWidth)
   for($i=1;$i -le $deck.Slides.Count;$i++){$deck.Slides.Item($i).Export((Join-Path $PSScriptRoot ($item[1]+'_'+$i+'.png')),'PNG',1600,$height)}
  } finally {$deck.Close()}
 }
} finally {[Runtime.InteropServices.Marshal]::ReleaseComObject($app)|Out-Null}
