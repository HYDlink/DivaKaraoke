# 部署伴奏支持提示与正式说明：备份旧文件，保留全部用户配置。
[CmdletBinding()]
param(
    # 游戏根目录参数：使用用户明确指定的本机安装目录，仅写入其MMFreeLyrics子目录。
    [string]$GameDirectory = 'E:\SteamLibrary\steamapps\common\Hatsune Miku Project DIVA Mega Mix Plus'
)
$ErrorActionPreference = 'Stop'
try {
    $supportRoot = Split-Path -Parent $PSScriptRoot
    $supportArtifact = Join-Path $supportRoot 'artifacts\non-vocal-support'
    $supportMod = Join-Path (Resolve-Path -LiteralPath $GameDirectory).Path 'mods\MMFreeLyrics'
    if (Get-Process -Name DivaMegaMix -ErrorAction SilentlyContinue) { throw '游戏仍在运行，请正常退出后再部署。' }
    $supportEntries = @(
        @{ Relative = 'MMFreeLyrics.dll'; Source = Join-Path $supportArtifact 'build\MMFreeLyrics.dll' },
        @{ Relative = 'MMFreeLyrics.pdb'; Source = Join-Path $supportArtifact 'build\MMFreeLyrics.pdb' },
        @{ Relative = 'docs\NON_VOCAL_SUPPORT.md'; Source = Join-Path $supportRoot 'docs\NON_VOCAL_SUPPORT.md' },
        @{ Relative = 'docs\NON_VOCAL_MVP.md'; Source = Join-Path $supportRoot 'docs\NON_VOCAL_MVP.md' },
        @{ Relative = 'docs\PV_TOOLS_MVP_ACCEPTANCE.md'; Source = Join-Path $supportRoot 'docs\PV_TOOLS_MVP_ACCEPTANCE.md' }
    )
    $supportPreserved = @{}
    foreach ($relative in @('config.toml', 'freelyrics.toml', 'singer-colors.toml', 'audio-tools.toml', 'obs-tools.toml')) {
        $file = Join-Path $supportMod $relative
        if (Test-Path -LiteralPath $file) { $supportPreserved[$relative] = (Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash }
    }
    foreach ($entry in $supportEntries) {
        $entry.Hash = (Get-FileHash -LiteralPath $entry.Source -Algorithm SHA256).Hash
        $entry.Target = [IO.Path]::GetFullPath((Join-Path $supportMod $entry.Relative))
        if (-not $entry.Target.StartsWith($supportMod + '\', [StringComparison]::OrdinalIgnoreCase)) { throw '部署目标超出指定模组目录。' }
    }
    $supportStamp = Get-Date -Format 'yyyyMMdd-HHmmss'
    $supportBackup = Join-Path $supportRoot "artifacts\deployment-backups\non-vocal-support-$supportStamp"
    $supportPackage = Join-Path $supportArtifact 'package'
    # 先完成包与全部旧文件备份，再替换游戏安装文件。
    foreach ($entry in $supportEntries) {
        $packageFile = Join-Path $supportPackage $entry.Relative
        [void](New-Item -ItemType Directory -Path (Split-Path -Parent $packageFile) -Force)
        Copy-Item -LiteralPath $entry.Source -Destination $packageFile -Force
        if (Test-Path -LiteralPath $entry.Target) {
            $backupFile = Join-Path $supportBackup $entry.Relative
            [void](New-Item -ItemType Directory -Path (Split-Path -Parent $backupFile) -Force)
            Copy-Item -LiteralPath $entry.Target -Destination $backupFile
            if ((Get-FileHash -LiteralPath $entry.Target -Algorithm SHA256).Hash -ne (Get-FileHash -LiteralPath $backupFile -Algorithm SHA256).Hash) { throw '旧文件备份哈希不一致，停止部署。' }
        }
    }
    Compress-Archive -Path (Join-Path $supportPackage '*') -DestinationPath (Join-Path $supportArtifact 'DivaNonVocalSupport.zip') -Force
    if (Get-Process -Name DivaMegaMix -ErrorAction SilentlyContinue) { throw '游戏刚刚启动，尚未替换文件，请正常退出后重试。' }
    foreach ($entry in $supportEntries) {
        [void](New-Item -ItemType Directory -Path (Split-Path -Parent $entry.Target) -Force)
        Copy-Item -LiteralPath $entry.Source -Destination $entry.Target -Force
        if ((Get-FileHash -LiteralPath $entry.Target -Algorithm SHA256).Hash -ne $entry.Hash) { throw "部署文件哈希不一致：$($entry.Relative)" }
    }
    foreach ($relative in $supportPreserved.Keys) {
        if ((Get-FileHash -LiteralPath (Join-Path $supportMod $relative) -Algorithm SHA256).Hash -ne $supportPreserved[$relative]) { throw "用户配置发生变化：$relative" }
    }
    $supportRecord = @{
        status = 'DEPLOYMENT VERIFIED'; game_running = $false; backup = $supportBackup
        files = @($supportEntries | ForEach-Object { @{ relative = $_.Relative; source = $_.Source; target = $_.Target; sha256 = $_.Hash } })
        preserved_settings = $supportPreserved; in_game = 'IN-GAME VERIFICATION REQUIRED'
    }
    $supportRecord | ConvertTo-Json -Depth 7 | Set-Content -LiteralPath (Join-Path $supportArtifact 'deployment.json') -Encoding UTF8
    Write-Output "伴奏提示部署通过：$($supportEntries.Count)份文件哈希一致，用户配置保持原哈希。"
    Write-Output "旧文件备份：$supportBackup"
} catch {
    Write-Error "伴奏提示部署失败：$($_.Exception.Message)"
    exit 1
}
