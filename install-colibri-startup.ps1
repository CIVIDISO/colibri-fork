param(
  [switch]$Remove
)

$repo = (Resolve-Path $PSScriptRoot).Path
$launcher = Join-Path $repo 'start-colibri.cmd'
$startup = [Environment]::GetFolderPath('Startup')
$shortcutPath = Join-Path $startup 'Colibri Companion.lnk'

if ($Remove) {
  if (Test-Path $shortcutPath) { Remove-Item $shortcutPath -Force }
  Write-Output "Removed Colibri startup shortcut."
  exit 0
}

$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $launcher
$shortcut.WorkingDirectory = $repo
$shortcut.Description = 'Start the local Colibri companion and workbench'
$shortcut.Save()
Write-Output "Installed Colibri startup shortcut: $shortcutPath"
