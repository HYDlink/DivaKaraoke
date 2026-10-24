# 使用独立管理员进程采集性能；不修改用户系统策略、游戏配置或已存在的记录。
[CmdletBinding()]
param(
    # 本次记录的名称，用于区分修改前和修复后的数据。
    [ValidatePattern('^[a-zA-Z0-9_-]+$')][string]$Name = 'pv261-baseline',
    # 自动停止的秒数上限，避免无人值守时持续记录。
    [ValidateRange(10, 300)][int]$DurationSeconds = 90,
    # 采集结果目录；ETL、状态及工具输出只保存在指定目录。
    [string]$OutputDirectory = (Join-Path (Split-Path -Parent $PSScriptRoot) 'artifacts\performance-investigation'),
    # 仅由提权后进程使用，避免递归打开 UAC。
    [switch]$Elevated
)
$ErrorActionPreference = 'Stop'
$recordRoot = [IO.Path]::GetFullPath($OutputDirectory)
[void](New-Item -ItemType Directory -Path $recordRoot -Force)
$recordStatus = Join-Path $recordRoot "$Name.status.json"
$recordTrace = Join-Path $recordRoot "$Name.etl"
$recordStop = Join-Path $recordRoot "$Name.stop"
$recordLog = Join-Path $recordRoot "$Name.wpr.log"

# 状态写入不依赖控制台窗口，主编排可以继续读取后台采集进度。
function Write-RecordStatus([string]$State, [string]$Message) {
    @{ 状态 = $State; 说明 = $Message; 记录 = $recordTrace; 时间 = [DateTimeOffset]::Now.ToString('o'); 进程 = $PID } |
        ConvertTo-Json | Set-Content -LiteralPath $recordStatus -Encoding UTF8
}

$recordIdentity = [Security.Principal.WindowsIdentity]::GetCurrent()
$recordPrincipal = [Security.Principal.WindowsPrincipal]::new($recordIdentity)
if (-not $recordPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    if ($Elevated) { throw 'Windows 未授予管理员权限，无法启动性能采集。' }
    Write-RecordStatus '等待授权' '请在 Windows UAC 弹窗中允许本次性能采集。'
    $recordArgs = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', ('"' + $PSCommandPath + '"'),
        '-Name', $Name, '-DurationSeconds', $DurationSeconds, '-OutputDirectory', ('"' + $recordRoot + '"'), '-Elevated')
    try {
        $recordProcess = Start-Process -FilePath (Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe') -ArgumentList $recordArgs -Verb RunAs -WindowStyle Hidden -PassThru
        Write-Output "已启动独立性能采集进程：$($recordProcess.Id)。"
    } catch {
        Write-RecordStatus '授权未完成' $_.Exception.Message
        throw '本次 Windows 管理员授权未完成；没有启动或取消任何性能记录。'
    }
    exit
}

$recordOwned = $false
try {
    if (Test-Path -LiteralPath $recordTrace) { throw '同名 ETL 已存在，请使用新的记录名称，避免覆盖证据。' }
    if (Test-Path -LiteralPath $recordStop) { Remove-Item -LiteralPath $recordStop }
    # 系统19041版本在本机保存ETL会报0x80010106，必须使用独立安装的新版工具。
    $recordCandidates = @(
        (Join-Path ${env:ProgramFiles(x86)} 'Windows Kits\10\Windows Performance Toolkit\wpr.exe'),
        (Join-Path $env:ProgramFiles 'Windows Kits\10\Windows Performance Toolkit\wpr.exe')
    )
    $recordWpr = $recordCandidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
    if (-not $recordWpr) { throw '未找到新版Windows Performance Toolkit；系统自带旧WPR无法可靠保存ETL，请先安装性能工具组件。' }
    # GeneralProfile 提供线程切换和等待栈；GPU 补充图形队列，保留 CPU 短卡顿证据。
    $recordProfile = (Join-Path $PSScriptRoot 'diva_performance.wprp') + '!DivaMod'
    # 独立重定向原生工具的错误流，避免 Windows PowerShell 将进度提示当成终止异常。
    $recordStartArgs = @('-start', 'GeneralProfile', '-start', 'GPU', '-start', ('"' + $recordProfile + '"'), '-filemode')
    $recordStart = Start-Process -FilePath $recordWpr -ArgumentList $recordStartArgs -WindowStyle Hidden -Wait -PassThru -RedirectStandardOutput (Join-Path $recordRoot "$Name.start.stdout.txt") -RedirectStandardError (Join-Path $recordRoot "$Name.start.stderr.txt")
    $recordCode = $recordStart.ExitCode
    "记录器启动退出码：$recordCode" | Set-Content -LiteralPath $recordLog -Encoding UTF8
    if ($recordCode -ne 0) { throw "性能记录器启动失败，错误码：$recordCode；详情保存在工具日志。" }
    $recordOwned = $true
    Write-RecordStatus '采集中' "正在记录 CPU 调用栈、线程等待、磁盘和 GPU；最多 $DurationSeconds 秒。"
    $recordDeadline = [DateTime]::UtcNow.AddSeconds($DurationSeconds)
    while ([DateTime]::UtcNow -lt $recordDeadline -and -not (Test-Path -LiteralPath $recordStop)) {
        Start-Sleep -Milliseconds 250
    }
    Write-RecordStatus '正在保存' '正在合并 ETL，请勿关闭采集进程。'
    $recordSaveArgs = @('-stop', ('"' + $recordTrace + '"'), '"PV261 歌词换句卡顿分析"')
    $recordSave = Start-Process -FilePath $recordWpr -ArgumentList $recordSaveArgs -WindowStyle Hidden -Wait -PassThru -RedirectStandardOutput (Join-Path $recordRoot "$Name.stop.stdout.txt") -RedirectStandardError (Join-Path $recordRoot "$Name.stop.stderr.txt")
    "记录器保存退出码：$($recordSave.ExitCode)" | Add-Content -LiteralPath $recordLog -Encoding UTF8
    if ($recordSave.ExitCode -ne 0 -or -not (Test-Path -LiteralPath $recordTrace)) { throw '性能记录保存失败，请查看工具日志；不会取消未知记录。' }
    $recordOwned = $false
    Write-RecordStatus '采集完成' 'ETL 已保存，等待分析真实调用栈及卡顿时间区间。'
} catch {
    Write-RecordStatus '采集失败' $_.Exception.Message
    # 只在确认本脚本成功创建记录后尝试保存，绝不取消用户已有的跟踪。
    if ($recordOwned) {
        $recordRecovery = Join-Path $recordRoot "$Name-recovery.etl"
        Start-Process -FilePath $recordWpr -ArgumentList @('-stop', ('"' + $recordRecovery + '"')) -WindowStyle Hidden -Wait | Out-Null
    }
    exit 1
}
