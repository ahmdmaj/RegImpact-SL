Add-Type -AssemblyName System.Runtime.WindowsRuntime

$null = [Windows.Globalization.Language, Windows.Globalization, ContentType = WindowsRuntime]
$null = [Windows.Graphics.Imaging.BitmapDecoder, Windows.Graphics.Imaging, ContentType = WindowsRuntime]
$null = [Windows.Media.Ocr.OcrEngine, Windows.Foundation, ContentType = WindowsRuntime]

$engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromUserProfileLanguages()
if ($engine) {
    Write-Output "WinRT OCR Engine created successfully: $($engine.RecognizerLanguage.LanguageTag)"
} else {
    Write-Output "WinRT OCR Engine is NULL"
}
