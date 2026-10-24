# 统一安装性能修复版及匹配符号，保留歌词、字体、配色、OBS和加载器开关。
[CmdletBinding()]
param(
    # 游戏根目录：只允许写入其中的 MMFreeLyrics 模组子目录。
    [string]$GameDirectory = 'E:\SteamLibrary\steamapps\common\Hatsune Miku Project DIVA Mega Mix Plus',
    # 用户要求直接使用时重新启用本模组；其余配置逐字保持。
    [switch]$EnableMod
)
$ErrorActionPreference = 'Stop'
$deployRoot = Split-Path -Parent $PSScriptRoot
$deployArtifact = Join-Path $deployRoot 'artifacts\performance-investigation'
$deployMod = Join-Path (Resolve-Path -LiteralPath $GameDirectory).Path 'mods\MMFreeLyrics'
if (Get-Process -Name DivaMegaMix -ErrorAction SilentlyContinue) { throw '游戏正在运行，必须正常退出后再部署；不会强制结束游戏。' }
$deployEntries = @(
    @{ Relative = 'MMFreeLyrics.dll'; Source = Join-Path $deployArtifact 'fixed-build\MMFreeLyrics.dll' },
    @{ Relative = 'MMFreeLyrics.pdb'; Source = Join-Path $deployArtifact 'fixed-build\MMFreeLyrics.pdb' },
    @{ Relative = 'docs\PERFORMANCE_INVESTIGATION.md'; Source = Join-Path $deployRoot 'docs\PERFORMANCE_INVESTIGATION.md' },
    @{ Relative = 'tools\record_mod_performance.ps1'; Source = Join-Path $deployRoot 'tools\record_mod_performance.ps1' },
    @{ Relative = 'tools\diva_performance.wprp'; Source = Join-Path $deployRoot 'tools\diva_performance.wprp' },
    @{ Relative = 'tools\PerfView.exe'; Source = Join-Path $deployArtifact 'tools\PerfView.exe' }
)
if ($EnableMod) {
    $enableConfig = [IO.File]::ReadAllText((Join-Path $deployMod 'config.toml'))
    $enablePattern = '(?m)^enabled[ \t]*=[ \t]*(false|true)[ \t]*(?=\r?$)'
    if ([regex]::Matches($enableConfig, $enablePattern).Count -ne 1) { throw '启用配置不唯一，拒绝自动修改。' }
    $enableSource = Join-Path $deployArtifact 'enabled-config.toml'
    [IO.File]::WriteAllText($enableSource, [regex]::Replace($enableConfig, $enablePattern, 'enabled = true'), [Text.UTF8Encoding]::new($false))
    $deployEntries += @{ Relative = 'config.toml'; Source = $enableSource }
}
$deployPreserved = @{}
foreach ($relative in @('config.toml', 'freelyrics.toml', 'singer-colors.toml', 'audio-tools.toml', 'obs-tools.toml')) {
    if ($EnableMod -and $relative -eq 'config.toml') { continue }
    $file = Join-Path $deployMod $relative
    if (Test-Path -LiteralPath $file) { $deployPreserved[$relative] = (Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash }
}
foreach ($entry in $deployEntries) {
    $entry.Hash = (Get-FileHash -LiteralPath $entry.Source -Algorithm SHA256).Hash
    $entry.Target = [IO.Path]::GetFullPath((Join-Path $deployMod $entry.Relative))
    if (-not $entry.Target.StartsWith($deployMod + '\', [StringComparison]::OrdinalIgnoreCase)) { throw '部署路径超出指定模组目录。' }
}
$deployStamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$deployBackup = Join-Path $deployRoot "artifacts\deployment-backups\performance-fix-$deployStamp"
$deployPackage = Join-Path $deployArtifact 'package'
if (Get-Process -Name DivaMegaMix -ErrorAction SilentlyContinue) { throw '游戏刚启动，已中止本次部署。' }
foreach ($entry in $deployEntries) {
    if (Test-Path -LiteralPath $entry.Target) {
        $backupFile = Join-Path $deployBackup $entry.Relative
        [void](New-Item -ItemType Directory -Path (Split-Path -Parent $backupFile) -Force)
        Copy-Item -LiteralPath $entry.Target -Destination $backupFile
    }
    [void](New-Item -ItemType Directory -Path (Split-Path -Parent $entry.Target) -Force)
    Copy-Item -LiteralPath $entry.Source -Destination $entry.Target -Force
    if ((Get-FileHash -LiteralPath $entry.Target -Algorithm SHA256).Hash -ne $entry.Hash) { throw "部署哈希不一致：$($entry.Relative)" }
    $packageFile = Join-Path $deployPackage $entry.Relative
    [void](New-Item -ItemType Directory -Path (Split-Path -Parent $packageFile) -Force)
    Copy-Item -LiteralPath $entry.Source -Destination $packageFile -Force
}
foreach ($relative in $deployPreserved.Keys) {
    if ((Get-FileHash -LiteralPath (Join-Path $deployMod $relative) -Algorithm SHA256).Hash -ne $deployPreserved[$relative]) {
        throw "用户配置发生变化：$relative"
    }
}
$deployRecord = @{
    status = 'DEPLOYMENT VERIFIED'; game_running = $false; backup = $deployBackup
    files = @($deployEntries | ForEach-Object { @{ relative = $_.Relative; source = $_.Source; target = $_.Target; sha256 = $_.Hash } })
    preserved_settings = $deployPreserved
    in_game = 'IN-GAME VERIFICATION REQUIRED'
}
$deployRecord | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $deployArtifact 'deployment.json') -Encoding UTF8
Compress-Archive -Path (Join-Path $deployPackage '*') -DestinationPath (Join-Path $deployArtifact 'DivaPerformanceFix.zip') -Force
Write-Output "部署通过：$($deployEntries.Count)份文件哈希一致；用户配置均保持原哈希。"
Write-Output "旧文件备份：$deployBackup"
Write-Output ($(if ($EnableMod) { 'Mod 已重新启用，启动游戏即可使用；游戏内流畅度仍需实际验收。' } else { 'Mod 启用状态保持用户当前设置；游戏内帧时间与录制仍需实际验收。' }))
