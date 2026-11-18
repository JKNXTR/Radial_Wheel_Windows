#Requires -Version 5.1
<# Деинсталатор на Radial Wheel (графичен, без конзола). Настройките (%APPDATA%\RadialWheel) се пазят, освен ако не изберете друго. #>
param([switch]$Relaunched, [switch]$RemoveSettings, [switch]$Quiet)

$ErrorActionPreference = 'Continue'
Add-Type -AssemblyName System.Windows.Forms
$AppName    = 'RadialWheel'
$Title      = 'Radial Wheel'
$InstallDir = Join-Path $env:LOCALAPPDATA $AppName

# Скриптът може да е в папката, която ще изтрием - изпълняваме копие от %TEMP%
$self = $MyInvocation.MyCommand.Path
if (-not $Relaunched -and $self -and $self -like "$InstallDir*") {
    $tmp = Join-Path $env:TEMP 'radialwheel-uninstall.ps1'
    Copy-Item $self $tmp -Force
    $a = @('-NoProfile','-WindowStyle','Hidden','-ExecutionPolicy','Bypass','-File',"`"$tmp`"",'-Relaunched')
    if ($RemoveSettings) { $a += '-RemoveSettings' }
    if ($Quiet) { $a += '-Quiet' }
    Start-Process powershell.exe -ArgumentList $a -WindowStyle Hidden
    exit 0
}

if (-not $Quiet) {
    $r = [Windows.Forms.MessageBox]::Show('Да премахна ли Radial Wheel от този компютър?', $Title, 'YesNo', 'Question')
    if ($r -ne 'Yes') { exit 0 }
    $r2 = [Windows.Forms.MessageBox]::Show('Да изтрия ли и личните настройки (config.json)?', $Title, 'YesNo', 'Question')
    if ($r2 -eq 'Yes') { $RemoveSettings = $true }
}

Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
    Where-Object { ($_.ExecutablePath -and $_.ExecutablePath -like "$InstallDir*") -or ($_.CommandLine -and $_.CommandLine -like "*$InstallDir*" -and $_.ProcessId -ne $PID) } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
Start-Sleep -Milliseconds 700

Remove-ItemProperty -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Run' -Name $AppName -ErrorAction SilentlyContinue
Remove-Item -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\$AppName" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item (Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs\Radial Wheel.lnk') -Force -ErrorAction SilentlyContinue
if (Test-Path $InstallDir) { Remove-Item $InstallDir -Recurse -Force -ErrorAction SilentlyContinue }
if ($RemoveSettings) { Remove-Item (Join-Path $env:APPDATA $AppName) -Recurse -Force -ErrorAction SilentlyContinue }

if (-not $Quiet) { [Windows.Forms.MessageBox]::Show('Radial Wheel е премахнат.', $Title, 'OK', 'Information') | Out-Null }
