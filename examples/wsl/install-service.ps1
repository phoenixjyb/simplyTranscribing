param([string]$Distro = 'Ubuntu-24.04', [string]$SourceRoot = '/opt/simply-transcribing')
$ErrorActionPreference = 'Stop'
$name = 'Local Transcriber WSL'
if (Get-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue) {
    throw 'Task already exists. Inspect it and the transcription queue before changing it.'
}
$userName = [Security.Principal.WindowsIdentity]::GetCurrent().Name
$action = New-ScheduledTaskAction -Execute "$env:WINDIR\System32\wsl.exe" -Argument "-d $Distro -- $SourceRoot/.venv/bin/python $SourceRoot/service.py"
$principal = New-ScheduledTaskPrincipal -UserId $userName -LogonType S4U -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit ([TimeSpan]::Zero) -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1) -MultipleInstances IgnoreNew -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
Register-ScheduledTask -TaskName $name -Action $action -Principal $principal -Settings $settings -Description 'On-demand isolated WSL transcription queue; does not wake the PC or load a model while idle.'
Start-ScheduledTask -TaskName $name
