param([string]$Distro = 'Ubuntu-24.04', [string]$SourceRoot = '/opt/simply-transcribing')
$ErrorActionPreference = 'Stop'
$name = 'Local Transcriber Web'
if (Get-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue) {
    throw 'Web task already exists. Inspect before changing it.'
}
$folder = Join-Path $env:USERPROFILE '.local-transcriber'
New-Item -ItemType Directory -Path $folder -Force | Out-Null
$launcher = Join-Path $folder 'start-web.ps1'
if (Test-Path $launcher) { throw 'Launcher already exists. Inspect before changing it.' }
@"
`$ErrorActionPreference = 'Stop'
& `$env:WINDIR\System32\wsl.exe -d '$Distro' -- $SourceRoot/.venv/bin/python $SourceRoot/app.py start
exit `$LASTEXITCODE
"@ | Set-Content -LiteralPath $launcher -Encoding UTF8
$userName = [Security.Principal.WindowsIdentity]::GetCurrent().Name
$action = New-ScheduledTaskAction -Execute "$env:WINDIR\System32\WindowsPowerShell\v1.0\powershell.exe" -Argument "-NoProfile -NonInteractive -ExecutionPolicy Bypass -File `"$launcher`""
$principal = New-ScheduledTaskPrincipal -UserId $userName -LogonType S4U -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit ([TimeSpan]::Zero) -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1) -MultipleInstances IgnoreNew -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
$trigger = New-ScheduledTaskTrigger -AtStartup
Register-ScheduledTask -TaskName $name -Action $action -Principal $principal -Settings $settings -Trigger $trigger -Description 'Private loopback transcription UI for Tailscale Serve. Starts its isolated worker; no model loaded when idle.' | Select-Object TaskName,State
Start-ScheduledTask -TaskName $name
