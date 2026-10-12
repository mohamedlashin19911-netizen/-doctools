param([string]$Path, [string]$OutFile, [string]$Lang = "auto")
[void][Windows.Globalization.Language,Windows.Foundation,ContentType=WindowsRuntime]
[void][Windows.Media.Ocr.OcrEngine,Windows.Foundation,ContentType=WindowsRuntime]
[void][Windows.Graphics.Imaging.BitmapDecoder,Windows.Foundation,ContentType=WindowsRuntime]
[void][Windows.Storage.StorageFile,Windows.Foundation,ContentType=WindowsRuntime]
Add-Type -AssemblyName System.Runtime.WindowsRuntime
$tm = [System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object { $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' } | Select-Object -First 1
function Await($op, $rt) { $t = $tm.MakeGenericMethod($rt).Invoke($null, @($op)); $t.Wait(-1) | Out-Null; $t.Result }
$engine = $null
if ($Lang -ne "auto") { $engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromLanguage((New-Object Windows.Globalization.Language ($Lang))) }
if ($null -eq $engine) { $engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromUserProfileLanguages() }
if ($null -eq $engine) { Write-Output "NO_ENGINE"; exit 1 }
$full = (Resolve-Path $Path).Path
$file = Await ([Windows.Storage.StorageFile]::GetFileFromPathAsync($full)) ([Windows.Storage.StorageFile])
$stream = Await ($file.OpenAsync([Windows.Storage.FileAccessMode]::Read)) ([Windows.Storage.Streams.IRandomAccessStream])
$dec = Await ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream)) ([Windows.Graphics.Imaging.BitmapDecoder])
$bmp = Await ($dec.GetSoftwareBitmapAsync()) ([Windows.Graphics.Imaging.SoftwareBitmap])
$res = Await ($engine.RecognizeAsync($bmp)) ([Windows.Media.Ocr.OcrResult])
$outLines = foreach ($line in $res.Lines) {
  $words = @($line.Words | ForEach-Object { [pscustomobject]@{ X = $_.BoundingBox.X; T = $_.Text } })
  $isRtl = ($line.Text -match "[\u0600-\u06FF]")
  if ($isRtl) { $sorted = $words | Sort-Object { -$_.X } } else { $sorted = $words | Sort-Object { $_.X } }
  ($sorted | ForEach-Object { $_.T }) -join " "
}
[System.IO.File]::WriteAllLines($OutFile, $outLines, (New-Object System.Text.UTF8Encoding($false)))
Write-Output ("ENGINE:" + $engine.RecognizerLanguage.LanguageTag)
