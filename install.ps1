#Requires -Version 5.1
<#
  Radial Wheel - графичен инсталатор (без конзола, без администраторски права).
  Инсталира приложението в %LOCALAPPDATA%\RadialWheel, регистрира автостарт с Windows,
  създава пряк път в Start менюто и стартира колелото (иконка в системната област).
  Ако до install.ps1 има dist\RadialWheel\RadialWheel.exe (build_exe.bat), Python не е нужен.
#>
param([switch]$NoLaunch)

$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
[System.Windows.Forms.Application]::EnableVisualStyles()

$AppName    = 'RadialWheel'
$Title      = 'Radial Wheel'
$Version    = '1.0.0'
$Src        = Split-Path -Parent $MyInvocation.MyCommand.Path
$InstallDir = Join-Path $env:LOCALAPPDATA $AppName
$AppDir     = Join-Path $InstallDir 'app'
$VenvDir    = Join-Path $InstallDir 'venv'
$BinDir     = Join-Path $InstallDir 'bin'
$LogFile    = Join-Path $InstallDir 'install.log'
$RunKey     = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Run'
$UninstKey  = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\$AppName"
$StartMenu  = Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs'
New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null

# ------------------------------------------------------------------ прозорец
$bg = [Drawing.Color]::FromArgb(43,43,43); $fg = [Drawing.Color]::FromArgb(236,230,212)
$form = New-Object Windows.Forms.Form
$form.Text = "Инсталация на $Title"; $form.ClientSize = New-Object Drawing.Size(580,400)
$form.StartPosition = 'CenterScreen'; $form.FormBorderStyle = 'FixedDialog'; $form.MaximizeBox = $false
$form.BackColor = $bg; $form.ForeColor = $fg; $form.Font = New-Object Drawing.Font('Segoe UI',10)
$ico = Join-Path $Src 'app\assets\app.ico'
if (Test-Path $ico) { $form.Icon = New-Object Drawing.Icon($ico) }

$lblTitle = New-Object Windows.Forms.Label
$lblTitle.Text = $Title; $lblTitle.Font = New-Object Drawing.Font('Segoe UI',18,[Drawing.FontStyle]::Bold)
$lblTitle.Location = New-Object Drawing.Point(20,14); $lblTitle.Size = New-Object Drawing.Size(540,36)
$lblSub = New-Object Windows.Forms.Label
$lblSub.Text = 'Радиално меню за бърз достъп и системно управление'
$lblSub.ForeColor = [Drawing.Color]::FromArgb(169,165,150)
$lblSub.Location = New-Object Drawing.Point(22,52); $lblSub.Size = New-Object Drawing.Size(540,22)
$lblStatus = New-Object Windows.Forms.Label
$lblStatus.Text = 'Подготовка...'; $lblStatus.Location = New-Object Drawing.Point(22,90); $lblStatus.Size = New-Object Drawing.Size(536,24)
$bar = New-Object Windows.Forms.ProgressBar
$bar.Location = New-Object Drawing.Point(22,120); $bar.Size = New-Object Drawing.Size(536,20); $bar.Minimum = 0; $bar.Maximum = 100
$logBox = New-Object Windows.Forms.TextBox
$logBox.Multiline = $true; $logBox.ReadOnly = $true; $logBox.ScrollBars = 'Vertical'
$logBox.BackColor = [Drawing.Color]::FromArgb(30,30,30); $logBox.ForeColor = [Drawing.Color]::FromArgb(190,190,190)
$logBox.Font = New-Object Drawing.Font('Consolas',9)
$logBox.Location = New-Object Drawing.Point(22,154); $logBox.Size = New-Object Drawing.Size(536,190)
$btn = New-Object Windows.Forms.Button
$btn.Text = 'Затвори'; $btn.Enabled = $false; $btn.FlatStyle = 'Flat'
$btn.Location = New-Object Drawing.Point(448,356); $btn.Size = New-Object Drawing.Size(110,30)
$btn.Add_Click({ $form.Close() })
$form.Controls.AddRange(@($lblTitle,$lblSub,$lblStatus,$bar,$logBox,$btn))
$script:busy = $true
$form.Add_FormClosing({ if ($script:busy) { $_.Cancel = $true } })

function Pump { [Windows.Forms.Application]::DoEvents() }
function Log([string]$msg) {
    $line = "[{0}] {1}" -f (Get-Date -Format 'HH:mm:ss'), $msg
    Add-Content -Path $LogFile -Value $line -Encoding UTF8
    $logBox.AppendText($line + "`r`n"); Pump
}
function Step([string]$text, [int]$pct) { $lblStatus.Text = $text; $bar.Value = $pct; Log $text }

function Invoke-Hidden([string]$exe, [string[]]$arguments) {
    # Скрит процес (без конзола); UI-ът остава отзивчив, докато чакаме
    $q = ($arguments | ForEach-Object { if ($_ -match '[\s"]') { '"' + ($_ -replace '"','\"') + '"' } else { $_ } }) -join ' '
    $o = Join-Path $env:TEMP 'rw_out.txt'; $e = Join-Path $env:TEMP 'rw_err.txt'
    $p = Start-Process -FilePath $exe -ArgumentList $q -WindowStyle Hidden -PassThru -RedirectStandardOutput $o -RedirectStandardError $e
    $null = $p.Handle
    while (-not $p.HasExited) { Pump; Start-Sleep -Milliseconds 80 }
    $p.WaitForExit()
    foreach ($f in $o,$e) { if (Test-Path $f) { Get-Content $f -ErrorAction SilentlyContinue | Select-Object -Last 15 | ForEach-Object { Add-Content $LogFile $_ -Encoding UTF8 }; Remove-Item $f -Force -ErrorAction SilentlyContinue } }
    if ($p.ExitCode -ne 0) { throw "Командата '$exe $q' върна код $($p.ExitCode). Подробности: $LogFile" }
}

function Test-Python([string]$exe, [string[]]$pre = @()) {
    try {
        $old = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
        $out = & $exe @pre -c "import sys;print('%d.%d'%sys.version_info[:2])" 2>$null
        $code = $LASTEXITCODE
        if ($code -eq 0 -and "$out" -match '^(\d+)\.(\d+)$') {
            $v = [version]"$out"
            if ($v -ge [version]'3.9' -and $v -lt [version]'3.14') {
                $path = & $exe @pre -c "import sys;print(sys.executable)" 2>$null
                $ErrorActionPreference = $old
                if ($path -and (Test-Path "$path")) { return "$path" }
            }
        }
        $ErrorActionPreference = $old
    } catch { }
    return $null
}

function Find-Python {
    $cands = @()
    foreach ($v in '3.12','3.13','3.11','3.10','3.9') { $cands += ,@('py', @("-$v")) }
    $cands += ,@('python', @())
    foreach ($v in '312','313','311','310','39') {
        $cands += ,@((Join-Path $env:LOCALAPPDATA "Programs\Python\Python$v\python.exe"), @())
        $cands += ,@((Join-Path $env:ProgramFiles "Python$v\python.exe"), @())
    }
    foreach ($c in $cands) {
        if ((Get-Command $c[0] -ErrorAction SilentlyContinue) -or (Test-Path $c[0])) {
            $p = Test-Python $c[0] $c[1]
            if ($p -and $p -notlike '*\WindowsApps\*') { return $p }
        }
    }
    return $null
}

function Install-Python {
    Step 'Инсталирам Python 3.12 (само за текущия потребител)...' 22
    $winget = Get-Command winget -ErrorAction SilentlyContinue
    if ($winget) {
        try { Invoke-Hidden 'winget' @('install','--id','Python.Python.3.12','-e','--scope','user','--silent','--accept-package-agreements','--accept-source-agreements') }
        catch { Log "winget неуспешно: $($_.Exception.Message)" }
        $p = Find-Python
        if ($p) { return $p }
    }
    $url = 'https://www.python.org/ftp/python/3.12.8/python-3.12.8-amd64.exe'
    $tmp = Join-Path $env:TEMP 'python-3.12.8-amd64.exe'
    Log "Изтеглям $url"
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    $wc = New-Object Net.WebClient
    $task = $wc.DownloadFileTaskAsync($url, $tmp)
    while (-not $task.IsCompleted) { Pump; Start-Sleep -Milliseconds 100 }
    if ($task.IsFaulted) { throw "Свалянето на Python е неуспешно: $($task.Exception.InnerException.Message)" }
    Invoke-Hidden $tmp @('/quiet','InstallAllUsers=0','PrependPath=0','Include_launcher=0','Include_test=0','Shortcuts=0')
    Remove-Item $tmp -Force -ErrorAction SilentlyContinue
    $p = Find-Python
    if (-not $p) { throw 'Python е инсталиран, но не може да бъде намерен. Инсталирайте Python 3.12 ръчно от python.org и стартирайте инсталатора отново.' }
    return $p
}

function New-Shortcut([string]$path, [string]$target, [string]$arguments, [string]$workdir, [string]$icon) {
    $ws = New-Object -ComObject WScript.Shell
    $lnk = $ws.CreateShortcut($path)
    $lnk.TargetPath = $target; $lnk.Arguments = $arguments; $lnk.WorkingDirectory = $workdir
    $lnk.IconLocation = $icon; $lnk.Description = 'Radial Wheel - радиално меню за бърз достъп'
    $lnk.Save()
}

# ------------------------------------------------------------------ инсталация
$form.Show(); Pump
$ok = $false
try {
    Log "=== Инсталация на $Title $Version ==="
    Step 'Спирам работеща версия...' 5
    Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
        Where-Object { ($_.ExecutablePath -and $_.ExecutablePath -like "$InstallDir*") -or ($_.CommandLine -and $_.CommandLine -like "*$InstallDir*" -and $_.ProcessId -ne $PID) } |
        ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
    Start-Sleep -Milliseconds 600; Pump

    if (-not (Test-Path (Join-Path $Src 'app\main.py'))) { throw "Не намирам app\main.py до install.ps1 ($Src). Разархивирайте целия ZIP, преди да инсталирате." }
    Step 'Копирам файловете на приложението...' 12
    & robocopy (Join-Path $Src 'app') $AppDir /MIR /XD __pycache__ /NFL /NDL /NJH /NJS /NP | Out-Null
    if ($LASTEXITCODE -ge 8) { throw "robocopy върна код $LASTEXITCODE" }
    Copy-Item (Join-Path $Src 'requirements.txt') $InstallDir -Force
    Copy-Item (Join-Path $Src 'uninstall.ps1') $InstallDir -Force

    $prebuilt = Join-Path $Src 'dist\RadialWheel\RadialWheel.exe'
    if (Test-Path $prebuilt) {
        Step 'Намерен е готов RadialWheel.exe - Python не е нужен.' 60
        & robocopy (Join-Path $Src 'dist\RadialWheel') $BinDir /MIR /NFL /NDL /NJH /NJS /NP | Out-Null
        if ($LASTEXITCODE -ge 8) { throw "robocopy върна код $LASTEXITCODE" }
        $Target = Join-Path $BinDir 'RadialWheel.exe'; $ShortcutArgs = ''; $LaunchArgs = ''
        $RunCmd = "`"$Target`" --autostart"; $WorkDir = $BinDir
    } else {
        Step 'Търся Python...' 18
        $py = Find-Python
        if (-not $py) { $py = Install-Python }
        Log "Python: $py"
        if (-not (Test-Path (Join-Path $VenvDir 'Scripts\pythonw.exe'))) {
            Step 'Създавам виртуална среда...' 30
            Invoke-Hidden $py @('-m','venv',$VenvDir)
        }
        $vpy = Join-Path $VenvDir 'Scripts\python.exe'
        Step 'Инсталирам зависимостите (PySide6, pycaw...) - до няколко минути...' 40
        Invoke-Hidden $vpy @('-m','pip','install','--disable-pip-version-check','--upgrade','pip')
        Invoke-Hidden $vpy @('-m','pip','install','--disable-pip-version-check','-r',(Join-Path $InstallDir 'requirements.txt'))
        Step 'Проверка на инсталацията...' 85
        Invoke-Hidden $vpy @('-c',"import sys; sys.path.insert(0, r'$AppDir'); import PySide6.QtWidgets, PySide6.QtSvg, radialwheel.app; print('OK')")
        $Target = Join-Path $VenvDir 'Scripts\pythonw.exe'
        $ShortcutArgs = "`"$AppDir\main.py`" --show"; $LaunchArgs = "`"$AppDir\main.py`""
        $RunCmd = "`"$Target`" `"$AppDir\main.py`" --autostart"; $WorkDir = $AppDir
    }

    Step 'Регистрирам автостартиране с Windows...' 90
    New-Item -Path $RunKey -Force | Out-Null
    Set-ItemProperty -Path $RunKey -Name $AppName -Value $RunCmd

    Step 'Създавам пряк път в Start менюто...' 94
    $icon = Join-Path $AppDir 'assets\app.ico'
    New-Shortcut (Join-Path $StartMenu "$Title.lnk") $Target $ShortcutArgs $WorkDir $icon
    New-Item -Path $UninstKey -Force | Out-Null
    $props = @{
        DisplayName = $Title; DisplayVersion = $Version; Publisher = 'Radial Wheel'; InstallLocation = $InstallDir; DisplayIcon = $icon
        UninstallString = "powershell.exe -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$InstallDir\uninstall.ps1`""
    }
    foreach ($k in $props.Keys) { Set-ItemProperty -Path $UninstKey -Name $k -Value $props[$k] }
    Set-ItemProperty -Path $UninstKey -Name NoModify -Value 1 -Type DWord
    Set-ItemProperty -Path $UninstKey -Name NoRepair -Value 1 -Type DWord

    if (-not $NoLaunch) {
        Step 'Стартирам Radial Wheel...' 98
        if ($LaunchArgs -eq '') { Start-Process -FilePath $Target -WorkingDirectory $WorkDir }
        else { Start-Process -FilePath $Target -ArgumentList $LaunchArgs -WorkingDirectory $WorkDir }
    }
    $bar.Value = 100
    $lblStatus.Text = 'Готово!'
    Log '=== Готово ==='
    $logBox.AppendText("`r`nКолелото работи във фонов режим (иконка до часовника) и се стартира при всяко зареждане на Windows.`r`nПокажете го с Ctrl+Alt+Space. Ако го затворите от иконата, клавишът пак го стартира.")
    $ok = $true
}
catch {
    Log ('ГРЕШКА: ' + $_.Exception.Message)
    Add-Content -Path $LogFile -Value ($_ | Out-String) -Encoding UTF8
    Add-Content -Path $LogFile -Value $_.ScriptStackTrace -Encoding UTF8
    $lblStatus.Text = 'Инсталацията е неуспешна'; $lblStatus.ForeColor = [Drawing.Color]::FromArgb(255,123,123)
    $logBox.AppendText("`r`n" + $_.ScriptStackTrace + "`r`nПълният лог: $LogFile")
}
$script:busy = $false
$btn.Enabled = $true
if (-not $ok) { [Windows.Forms.MessageBox]::Show("Инсталацията е неуспешна.`n`n$($Error[0].Exception.Message)`n`nЛог: $LogFile", $Title, 'OK', 'Error') | Out-Null }
while ($form.Visible) { Pump; Start-Sleep -Milliseconds 50 }
if ($ok) { exit 0 } else { exit 1 }
