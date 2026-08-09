# make-shortcuts.ps1 — Create 2 desktop shortcut (.lnk) files for Google_blog servers
#
# Usage (PowerShell):
#   cd D:\Google_blog
#   .\make-shortcuts.ps1
#
# Result: 2 .lnk files on Desktop
#   - "Ollama Server (Google_blog).lnk"
#   - "wp-auto UI (Google_blog).lnk"
#
# Or run start-both.bat directly — it already launches both servers in
# separate windows. Desktop shortcuts are for one-click access.

$wpAutoDir = 'D:\Google_blog\wp-auto'
$desktop = [Environment]::GetFolderPath('Desktop')

if (-not (Test-Path $wpAutoDir)) {
    Write-Host "[ERROR] $wpAutoDir not found" -ForegroundColor Red
    exit 1
}

$shell = New-Object -ComObject WScript.Shell

# 1) Ollama Server shortcut
$ollamaLink = Join-Path $desktop 'Ollama Server (Google_blog).lnk'
$ollamaShortcut = $shell.CreateShortcut($ollamaLink)
$ollamaShortcut.TargetPath = Join-Path $wpAutoDir 'start-ollama.bat'
$ollamaShortcut.WorkingDirectory = $wpAutoDir
$ollamaShortcut.WindowStyle = 1
$ollamaShortcut.IconLocation = 'shell32.dll,13'
$ollamaShortcut.Description = 'Ollama server (qwen2.5:7b, CPU mode for GTX 1050)'
$ollamaShortcut.Save()

# 2) wp-auto UI shortcut
$uiLink = Join-Path $desktop 'wp-auto UI (Google_blog).lnk'
$uiShortcut = $shell.CreateShortcut($uiLink)
$uiShortcut.TargetPath = Join-Path $wpAutoDir 'start-wp-auto.bat'
$uiShortcut.WorkingDirectory = $wpAutoDir
$uiShortcut.WindowStyle = 1
$uiShortcut.IconLocation = 'shell32.dll,12'
$uiShortcut.Description = 'wp-auto Web UI (FastAPI, port 8767)'
$uiShortcut.Save()

Write-Host ""
Write-Host "[OK] 2 desktop shortcuts created:" -ForegroundColor Green
Write-Host "  - $ollamaLink"
Write-Host "  - $uiLink"
Write-Host ""
Write-Host "Double-click either shortcut to start the server."
Write-Host "Use start-both.bat to start both at once."
