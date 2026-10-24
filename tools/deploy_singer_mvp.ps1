# 歌手配色MVP部署：只替换本模组DLL、离线工具和歌手旁路，保留字幕、字体及用户设置。
[CmdletBinding()]
param(
    # 游戏根目录参数：默认使用用户明确指定的本机安装目录。
    [string]$GameDirectory = 'E:\SteamLibrary\steamapps\common\Hatsune Miku Project DIVA Mega Mix Plus'
)
$ErrorActionPreference = 'Stop'
try {
    $singerProjectRoot = Split-Path -Parent $PSScriptRoot
    $singerGameRoot = (Resolve-Path -LiteralPath $GameDirectory).Path
    $singerModRoot = Join-Path $singerGameRoot 'mods\MMFreeLyrics'
    if (Get-Process -Name DivaMegaMix -ErrorAction SilentlyContinue) { throw '游戏正在运行，请正常退出游戏后重新执行；不会强制结束游戏。' }
    $singerEntries = @(
        @{ Relative = 'MMFreeLyrics.dll'; Source = Join-Path $singerProjectRoot 'artifacts\singer-mvp\build\MMFreeLyrics.dll' },
        @{ Relative = 'tools\build_singer_timeline.py'; Source = Join-Path $singerProjectRoot 'scripts\build_singer_timeline.py' },
        @{ Relative = 'tools\extract_native_lyric_timeline.py'; Source = Join-Path $singerProjectRoot 'scripts\extract_native_lyric_timeline.py' },
        @{ Relative = 'tools\build_singer_colors.cmd'; Source = Join-Path $singerProjectRoot 'tools\build_singer_colors.cmd' },
        @{ Relative = 'docs\SINGER_COLORS_MVP.md'; Source = Join-Path $singerProjectRoot 'docs\SINGER_COLORS_MVP.md' },
        @{ Relative = 'docs\CHORUS_COLOR_DESIGNS.md'; Source = Join-Path $singerProjectRoot 'docs\CHORUS_COLOR_DESIGNS.md' },
        @{ Relative = 'docs\assets\chorus-colors\chorus-vertical.png'; Source = Join-Path $singerProjectRoot 'docs\assets\chorus-colors\chorus-vertical.png' },
        @{ Relative = 'docs\assets\chorus-colors\chorus-marker.png'; Source = Join-Path $singerProjectRoot 'docs\assets\chorus-colors\chorus-marker.png' },
        @{ Relative = 'docs\assets\chorus-colors\chorus-horizontal.png'; Source = Join-Path $singerProjectRoot 'docs\assets\chorus-colors\chorus-horizontal.png' }
    )
    $singerPrevious = @{}
    $singerManifestPath = Join-Path $singerModRoot 'singer-mvp-manifest.json'
    if (Test-Path -LiteralPath $singerManifestPath) {
        foreach ($entry in (Get-Content -Raw -Encoding UTF8 -LiteralPath $singerManifestPath | ConvertFrom-Json).files) { $singerPrevious[$entry.relative] = $entry.sha256 }
    }
    foreach ($pv in @(41,62,728,802,611,268)) {
        $stem = 'PV{0:000}' -f $pv
        $sourceSrt = Join-Path $singerProjectRoot "artifacts\furigana-official-alignment\cache\$stem.srt"
        $targetSrt = Join-Path $singerModRoot "lyrics\$stem.srt"
        if ((Get-FileHash -Algorithm SHA256 -LiteralPath $sourceSrt).Hash -ne (Get-FileHash -Algorithm SHA256 -LiteralPath $targetSrt).Hash) { throw "$stem 字幕与已验证来源不一致，拒绝部署错行颜色。" }
        $relative = "lyrics\$stem.singers.tsv"
        $source = Join-Path $singerProjectRoot "artifacts\singer-mvp\cache\$stem.singers.tsv"
        $target = Join-Path $singerModRoot $relative
        if (Test-Path -LiteralPath $target) {
            $actual = (Get-FileHash -Algorithm SHA256 -LiteralPath $target).Hash
            if ($actual -ne (Get-FileHash -Algorithm SHA256 -LiteralPath $source).Hash -and $actual -ne $singerPrevious[$relative]) { throw "$stem 歌手标记可能有用户修改，拒绝覆盖。" }
        }
        $singerEntries += @{ Relative = $relative; Source = $source }
    }
    # 先核对全部源文件和目标范围，之后才开始备份和替换。
    foreach ($entry in $singerEntries) {
        $entry.Hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $entry.Source).Hash
        $entry.Target = [IO.Path]::GetFullPath((Join-Path $singerModRoot $entry.Relative))
        if (-not $entry.Target.StartsWith($singerModRoot + '\', [StringComparison]::OrdinalIgnoreCase)) { throw '部署目标越出指定模组目录。' }
    }
    $singerStamp = Get-Date -Format 'yyyyMMdd-HHmmss'
    if (Get-Process -Name DivaMegaMix -ErrorAction SilentlyContinue) { throw '游戏刚刚启动，已中止部署；请正常退出后再执行。' }
    $singerBackup = Join-Path $singerProjectRoot "artifacts\deployment-backups\singer-mvp-$singerStamp"
    $singerPackage = Join-Path $singerProjectRoot 'artifacts\singer-mvp\package'
    foreach ($entry in $singerEntries) {
        if (Test-Path -LiteralPath $entry.Target) {
            $backup = Join-Path $singerBackup $entry.Relative
            [void](New-Item -ItemType Directory -Path (Split-Path -Parent $backup) -Force)
            Copy-Item -LiteralPath $entry.Target -Destination $backup
        }
        [void](New-Item -ItemType Directory -Path (Split-Path -Parent $entry.Target) -Force)
        Copy-Item -LiteralPath $entry.Source -Destination $entry.Target -Force
        if ((Get-FileHash -Algorithm SHA256 -LiteralPath $entry.Target).Hash -ne $entry.Hash) { throw "部署哈希不一致：$($entry.Relative)" }
        $packageFile = Join-Path $singerPackage $entry.Relative
        [void](New-Item -ItemType Directory -Path (Split-Path -Parent $packageFile) -Force)
        Copy-Item -LiteralPath $entry.Source -Destination $packageFile -Force
    }
    $singerRecord = @{ status = 'DEPLOYMENT VERIFIED'; game_running = $false; backup = $singerBackup; files = @($singerEntries | ForEach-Object { @{ relative = $_.Relative; source = $_.Source; target = $_.Target; sha256 = $_.Hash } }) }
    $singerJson = $singerRecord | ConvertTo-Json -Depth 8
    Set-Content -Encoding UTF8 -LiteralPath $singerManifestPath -Value $singerJson
    Set-Content -Encoding UTF8 -LiteralPath (Join-Path $singerProjectRoot 'artifacts\singer-mvp\deployment.json') -Value $singerJson
    Compress-Archive -LiteralPath $singerPackage -DestinationPath (Join-Path $singerProjectRoot 'artifacts\singer-mvp\DivaSingerColors-MVP.zip') -Force
    Write-Output "部署通过：$($singerEntries.Count)份文件哈希全部一致。"
    Write-Output "旧文件备份：$singerBackup"
    Write-Output '歌词、振假名、字体、OBS和已有颜色设置均保留；游戏内效果仍需实际验收。'
} catch {
    Write-Error "部署失败：$($_.Exception.Message)"
    exit 1
}
