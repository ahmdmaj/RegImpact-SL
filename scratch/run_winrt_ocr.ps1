param (
    [string]$ImagePath,
    [string]$OutPath
)

Add-Type -AssemblyName System.Runtime.WindowsRuntime

# Helper to await WinRT IAsyncOperation
$asTaskGeneric = [System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {
    $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1'
}

function Await-WinRT ($asyncOp, [Type]$returnType) {
    $asTask = $asTaskGeneric.MakeGenericMethod($returnType)
    $netTask = $asTask.Invoke($null, @($asyncOp))
    $netTask.Wait(-1) | Out-Null
    return $netTask.Result
}

$null = [Windows.Storage.StorageFile, Windows.Storage, ContentType = WindowsRuntime]
$null = [Windows.Graphics.Imaging.BitmapDecoder, Windows.Graphics.Imaging, ContentType = WindowsRuntime]
$null = [Windows.Media.Ocr.OcrEngine, Windows.Foundation, ContentType = WindowsRuntime]

$fullPath = (Resolve-Path $ImagePath).Path
$fileAsync = [Windows.Storage.StorageFile]::GetFileFromPathAsync($fullPath)
$file = Await-WinRT $fileAsync ([Windows.Storage.StorageFile])

$streamAsync = $file.OpenAsync([Windows.Storage.FileAccessMode]::Read)
$stream = Await-WinRT $streamAsync ([Windows.Storage.Streams.IRandomAccessStream])

$decoderAsync = [Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream)
$decoder = Await-WinRT $decoderAsync ([Windows.Graphics.Imaging.BitmapDecoder])

$bitmapAsync = $decoder.GetSoftwareBitmapAsync()
$bitmap = Await-WinRT $bitmapAsync ([Windows.Graphics.Imaging.SoftwareBitmap])

$engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromUserProfileLanguages()
$ocrAsync = $engine.RecognizeAsync($bitmap)
$ocrResult = Await-WinRT $ocrAsync ([Windows.Media.Ocr.OcrResult])

$lines = @()
foreach ($line in $ocrResult.Lines) {
    $lines += $line.Text
}

$fullText = $lines -join "`r`n"
Set-Content -Path $OutPath -Value $fullText -Encoding utf8
Write-Output "OCR completed for $ImagePath -> $OutPath ($($lines.Count) lines recognized)"
