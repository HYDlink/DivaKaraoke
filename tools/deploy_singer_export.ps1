# 自动歌手导出部署：动态读取成功清单，备份并安装工具与派生数据，保留人工修订和用户配置。
[CmdletBinding()]
param(
    # 游戏目录参数：使用用户指定的本机安装位置。
    [string]$GameDirectory = 'E:\SteamLibrary\steamapps\common\Hatsune Miku Project DIVA Mega Mix Plus',
    # 已成功生成的缓存目录参数：包含版本3导出清单。
    [string]$CacheDirectory = ''
)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
if (-not $CacheDirectory) {
    $CacheDirectory = Join-Path $projectRoot 'artifacts\singer-full-export\cache'
    if (-not (Test-Path -LiteralPath $CacheDirectory)) { $CacheDirectory = Join-Path $projectRoot 'artifacts\exported-lyrics\cache' }
}
$cacheRoot = (Resolve-Path -LiteralPath $CacheDirectory).Path
$cacheOutput = Split-Path -Parent $cacheRoot
$modRoot = Join-Path (Resolve-Path -LiteralPath $GameDirectory).Path 'mods\MMFreeLyrics'
$manifest = Get-Content -Raw -Encoding UTF8 -LiteralPath (Join-Path $cacheRoot 'export-manifest.json') | ConvertFrom-Json
if ($manifest.schema_version -ne 3) { throw '缓存尚未完成歌手生成，拒绝部署。' }
$entries = @()
foreach ($relative in @('scripts\export_lyrics.py','scripts\build_singer_timeline.py','scripts\extract_native_lyric_timeline.py','tools\export_lyrics.cmd','tools\build_singer_colors.cmd','tools\apply_singer_marks.cmd','tools\deploy_singer_export.ps1','docs\SINGER_EXPORT_WORKFLOW.md','docs\LYRICS_EXPORTER_MVP.md','docs\SINGER_COLORS_MVP.md','docs\CHORUS_COLOR_DESIGNS.md','docs\assets\chorus-colors\chorus-vertical.png','docs\assets\chorus-colors\chorus-marker.png','docs\assets\chorus-colors\chorus-horizontal.png')) {
    $entries += @{ Relative=$relative; Source=(Join-Path $projectRoot $relative) }
}
$entries += @{Relative='tools\build_singer_timeline.py'; Source=(Join-Path $projectRoot 'scripts\build_singer_timeline.py')}
$entries += @{Relative='tools\extract_native_lyric_timeline.py'; Source=(Join-Path $projectRoot 'scripts\extract_native_lyric_timeline.py')}
foreach ($file in Get-ChildItem -LiteralPath $cacheRoot -File) {
    if ($file.Name -match '^(PV[0-9]+\.(json|srt|ruby\.tsv|ruby\.audit\.json|singers\.tsv|singers\.audit\.json|singers\.md)|export-manifest\.json|singer-scan\.(json|md))$') {
        $entries += @{Relative=('artifacts\exported-lyrics\cache\'+$file.Name);Source=$file.FullName}
    }
}
$manualSource = Join-Path $cacheOutput 'manual-singers'
foreach ($file in Get-ChildItem -LiteralPath $manualSource -Filter 'PV*.singers.manual.tsv' -File) {
    $relative = 'artifacts\exported-lyrics\manual-singers\'+$file.Name
    $target = Join-Path $modRoot $relative
    if (Test-Path -LiteralPath $target) {
        $existing = [IO.File]::ReadAllText($target).TrimStart([char]0xFEFF).Replace("`r`n","`n")
        $incoming = [IO.File]::ReadAllText($file.FullName).TrimStart([char]0xFEFF).Replace("`r`n","`n")
        if ($existing -ne $incoming) { throw ('检测到独立人工修订，请先用--manual-singers-dir指向现有人工目录重新生成：'+$target) }
        continue
    }
    $entries += @{Relative=$relative;Source=$file.FullName}
}
foreach ($entry in $entries) {
    $entry.Hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $entry.Source).Hash
    $entry.Target = [IO.Path]::GetFullPath((Join-Path $modRoot $entry.Relative))
    if (-not $entry.Target.StartsWith($modRoot+'\',[StringComparison]::OrdinalIgnoreCase)) { throw '目标越出指定模组目录。' }
}
$backup = Join-Path $projectRoot ('artifacts\deployment-backups\singer-export-'+(Get-Date -Format 'yyyyMMdd-HHmmss'))
$backupNames = @($entries | ForEach-Object {$_.Relative})
$backupNames += 'lyrics\export-install-manifest.json'
foreach ($song in $manifest.entries) { foreach ($file in $song.files) { $backupNames += 'lyrics\'+$file.file } }
# 旧六曲MVP可能留下现在为同身份的旁路，备份后由统一安装器按哈希安全回收。
$legacy = Join-Path $modRoot 'singer-mvp-manifest.json'
if (Test-Path -LiteralPath $legacy) { $backupNames += @( (Get-Content -Raw -Encoding UTF8 -LiteralPath $legacy | ConvertFrom-Json).files | Where-Object {$_.relative -match '^lyrics[\\/]PV[0-9]+\.singers\.tsv$'} | ForEach-Object {$_.relative}) }
foreach ($relative in $backupNames | Sort-Object -Unique) {
    $source = [IO.Path]::GetFullPath((Join-Path $modRoot $relative))
    if (-not $source.StartsWith($modRoot+'\',[StringComparison]::OrdinalIgnoreCase)) { throw '备份路径越界。' }
    if (Test-Path -LiteralPath $source -PathType Leaf) {
        $target = Join-Path $backup $relative
        [void](New-Item -ItemType Directory -Path (Split-Path -Parent $target) -Force)
        Copy-Item -LiteralPath $source -Destination $target
    }
}
$dllBefore = (Get-FileHash -LiteralPath (Join-Path $modRoot 'MMFreeLyrics.dll') -Algorithm SHA256).Hash
& python (Join-Path $projectRoot 'scripts\export_lyrics.py') --output-dir $cacheOutput --install-only --install-dir (Join-Path $modRoot 'lyrics')
if ($LASTEXITCODE -ne 0) { throw '统一歌词/注音/歌手安装预检未通过；工具及人工模板尚未替换。' }
$package = Join-Path $cacheOutput 'package'
foreach ($entry in $entries) {
    [void](New-Item -ItemType Directory -Path (Split-Path -Parent $entry.Target) -Force)
    if ($entry.Source -ne $entry.Target) { Copy-Item -LiteralPath $entry.Source -Destination $entry.Target -Force }
    if ((Get-FileHash -LiteralPath $entry.Target -Algorithm SHA256).Hash -ne $entry.Hash) { throw ('工具或缓存部署哈希不一致：'+$entry.Relative) }
    $packed = Join-Path $package $entry.Relative
    [void](New-Item -ItemType Directory -Path (Split-Path -Parent $packed) -Force)
    Copy-Item -LiteralPath $entry.Source -Destination $packed -Force
}
foreach ($song in $manifest.entries) { foreach ($file in $song.files) {
    if ((Get-FileHash -LiteralPath (Join-Path $modRoot ('lyrics\'+$file.file)) -Algorithm SHA256).Hash.ToLowerInvariant() -ne $file.sha256.ToLowerInvariant()) { throw ('安装旁路哈希不匹配：'+$file.file) }
} }
if ((Get-FileHash -LiteralPath (Join-Path $modRoot 'MMFreeLyrics.dll') -Algorithm SHA256).Hash -ne $dllBefore) { throw '工具部署意外改变了DLL。' }
$record = @{status='DEPLOYMENT VERIFIED';backup=$backup;dll_sha256=$dllBefore;runtime_files=@($manifest.entries | ForEach-Object {$_.files}).Count;singer_generation=$manifest.singer_generation;files=@($entries | ForEach-Object {@{relative=$_.Relative;target=$_.Target;sha256=$_.Hash}})}
$record | ConvertTo-Json -Depth 9 | Set-Content -Encoding UTF8 -LiteralPath (Join-Path $cacheOutput 'deployment.json')
Compress-Archive -LiteralPath $package -DestinationPath (Join-Path $cacheOutput 'DivaSingerExport.zip') -Force
Write-Output ('部署通过：'+$manifest.singer_generation.generated+'首歌手旁路，全部文件哈希正确。')
Write-Output ('旧文件备份：'+$backup)
Write-Output 'DLL与用户配置保持原样，人工标记文件不覆盖，后续可通过短入口重新应用。'
