param([string]$DeckPath,[string]$OutputStem)
$ErrorActionPreference='Stop'
$deckFile=(Resolve-Path -LiteralPath $DeckPath).Path
$destStem=[System.IO.Path]::GetFullPath($OutputStem)
$ppApp=New-Object -ComObject PowerPoint.Application
$initialCount=$ppApp.Presentations.Count
$report=@()
try {
 $pres=$ppApp.Presentations.Open($deckFile,$true,$false,$false)
 try {
  foreach($slide in $pres.Slides){
   $textItems=@();$imageCount=0
   foreach($shape in $slide.Shapes){
    if($shape.Type -eq 13){$imageCount++}
    if($shape.HasTextFrame -and $shape.TextFrame.HasText){
     $r=$shape.TextFrame2.TextRange
     $textItems+=[ordered]@{text=$r.Text;width=$shape.Width;height=$shape.Height;boundWidth=$r.BoundWidth;boundHeight=$r.BoundHeight;rotation=$shape.Rotation;fontSize=$r.Font.Size}
    }
   }
   $slide.Export(($destStem+'.slide'+$slide.SlideIndex+'.png'),'PNG',1840,[int](1840*$pres.PageSetup.SlideHeight/$pres.PageSetup.SlideWidth))
   $report+=[ordered]@{slide=$slide.SlideIndex;shapes=$slide.Shapes.Count;images=$imageCount;textItems=$textItems}
  }
  $pres.SaveAs(($destStem+'.pdf'),32)
 } finally {$pres.Close()}
} finally {
 if($initialCount -eq 0 -and $ppApp.Presentations.Count -eq 0){$ppApp.Quit()}
 [System.Runtime.InteropServices.Marshal]::ReleaseComObject($ppApp)|Out-Null
}
$report|ConvertTo-Json -Depth 8|Set-Content -LiteralPath ($destStem+'.inspection.json') -Encoding utf8
Write-Output ('PowerPoint opened and exported '+$deckFile)
