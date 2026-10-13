#requires -Version 7.0
# 将已提交源码与本机可用运行文件保存为私有恢复快照；只读取游戏目录。
param(
    # 快照目录名称；不允许覆盖已有快照。
    [string]$SnapshotName = ('local-' + (Get-Date -Format 'yyyyMMdd-HHmmss')),
    # 已安装模组目录，包含实际 DLL、歌词、字体及私人 OBS 配置。
    [string]$GameModDirectory = 'E:\SteamLibrary\steamapps\common\Hatsune Miku Project DIVA Mega Mix Plus\mods\MMFreeLyrics'
)

$ErrorActionPreference = 'Stop'
$repoRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
if ($SnapshotName -notmatch '^[a-zA-Z0-9][a-zA-Z0-9_-]*$') {
    throw '快照名称只能包含英文字母、数字、短横线和下划线。'
}
$snapshotRoot = Join-Path $repoRoot ('artifacts/local-snapshots/' + $SnapshotName)

# 执行本地 Git 命令，将失败原因包含在中文错误提示中。
function Invoke-LocalGit {
    # 仓库目录及 Git 参数数组。
    param([string]$Directory, [string[]]$GitArguments)
    $result = & git -C $Directory @GitArguments 2>&1
    if ($LASTEXITCODE -ne 0) { throw ('本地 Git 操作失败：' + ($result -join "`n")) }
    return ($result -join "`n")
}

# 创建压缩包并逐文件读取压缩包内容核对 SHA-256，源文件改变时立即失败。
function New-VerifiedArchive {
    # 压缩包名称、来源根目录及必须保存的相对路径。
    param([string]$Name, [string]$Root, [string[]]$Includes)
    $rootPath = [IO.Path]::GetFullPath($Root).TrimEnd('\', '/') + [IO.Path]::DirectorySeparatorChar
    $files = @(
        foreach ($item in $Includes) {
            $path = Join-Path $Root $item
            if (-not (Test-Path -LiteralPath $path)) { throw ('快照必需文件不存在：' + $path) }
            Get-ChildItem -LiteralPath $path -File -Recurse -Force
        }
    ) | Sort-Object FullName -Unique | Where-Object {
        $_.Name -ne '.git' -and
        $_.FullName -notmatch '\\(\.git|__pycache__|backup|backups|obj)\\' -and
        $_.Name -notmatch '(\.before-|\.before\.|^config\.before-|^obs-helper\.state)' -and
        $_.Extension -notin @('.log', '.pyc', '.pyo', '.tmp')
    }
    $archivePath = Join-Path $snapshotRoot ($Name + '.zip')
    $records = [Collections.Generic.List[object]]::new()
    $archive = [IO.Compression.ZipFile]::Open($archivePath, [IO.Compression.ZipArchiveMode]::Create)
    try {
        foreach ($file in $files) {
            $relative = $file.FullName.Substring($rootPath.Length).Replace('\', '/')
            $hash = (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash
            [IO.Compression.ZipFileExtensions]::CreateEntryFromFile(
                $archive, $file.FullName, $relative, [IO.Compression.CompressionLevel]::Optimal
            ) | Out-Null
            $records.Add([pscustomobject]@{ path = $relative; bytes = $file.Length; sha256 = $hash })
        }
    } finally { $archive.Dispose() }
    $archive = [IO.Compression.ZipFile]::OpenRead($archivePath)
    try {
        if ($archive.Entries.Count -ne $records.Count) { throw '恢复包文件数量不一致。' }
        foreach ($record in $records) {
            $entry = $archive.GetEntry($record.path)
            $stream = $entry.Open()
            $sha = [Security.Cryptography.SHA256]::Create()
            try { $actual = [BitConverter]::ToString($sha.ComputeHash($stream)).Replace('-', '') }
            finally { $stream.Dispose(); $sha.Dispose() }
            if ($actual -ne $record.sha256 -or $entry.Length -ne $record.bytes) {
                throw ('恢复包校验失败，源文件可能正在改变：' + $record.path)
            }
        }
    } finally { $archive.Dispose() }
    $records.ToArray() | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $snapshotRoot ($Name + '-files.json')) -Encoding utf8
    Write-Output ('已校验恢复包：' + $Name + '，文件数：' + $records.Count)
    return [pscustomobject]@{
        name = $Name + '.zip'; files = $records.Count
        bytes = (Get-Item -LiteralPath $archivePath).Length
        sha256 = (Get-FileHash -LiteralPath $archivePath -Algorithm SHA256).Hash
    }
}

# 将进度输出从返回数据中分离，保持快照清单为纯结构化记录。
function Save-ArchiveRecord {
    # 压缩包名称、来源根目录及必须保存的相对路径。
    param([string]$Name, [string]$Root, [string[]]$Includes)
    $result = @(New-VerifiedArchive -Name $Name -Root $Root -Includes $Includes)
    foreach ($value in $result) {
        if ($value -is [string]) { Write-Host $value }
        else { $archiveRecords.Add($value) }
    }
}

$status = Invoke-LocalGit -Directory $repoRoot -GitArguments @('status', '--porcelain')
if ($status) { throw '请先提交源码及子模块版本，再创建快照；当前工作区仍有未提交内容。' }
if (Test-Path -LiteralPath $snapshotRoot) { throw '快照目录已存在，请使用新名称；不会覆盖已有记录。' }
New-Item -ItemType Directory -Path $snapshotRoot | Out-Null
Add-Type -AssemblyName System.IO.Compression.FileSystem
$archiveRecords = [Collections.Generic.List[object]]::new()
Save-ArchiveRecord -Name 'installed-mod-private' -Root $GameModDirectory -Includes @(
    'MMFreeLyrics.dll', 'config.toml', 'freelyrics.toml', 'lyrics', 'fonts', 'tools', 'scripts',
    'docs', 'MikuMikuLibrary', 'artifacts'
)
Save-ArchiveRecord -Name 'workspace-support' -Root $repoRoot -Includes @(
    'MikuMikuLibrary', 'tools/furigana_runtime', 'tools/obs_runtime',
    'artifacts/Open-PD-Script-Editor', 'artifacts/installed-native-lyric-sources.json'
)
Save-ArchiveRecord -Name 'build-dependencies' -Root $repoRoot -Includes @('Dependencies')
$bundlePath = Join-Path $snapshotRoot 'source.bundle'
Invoke-LocalGit -Directory $repoRoot -GitArguments @('bundle', 'create', $bundlePath, '--all') | Out-Null
Invoke-LocalGit -Directory $repoRoot -GitArguments @('bundle', 'verify', $bundlePath) | Out-Null
$dependencyVersions = @(
    foreach ($path in @('Dependencies/imgui', 'Dependencies/srtparser', 'Dependencies/toml11', 'artifacts/Open-PD-Script-Editor')) {
        [pscustomobject]@{ path = $path; commit = Invoke-LocalGit -Directory (Join-Path $repoRoot $path) -GitArguments @('rev-parse', 'HEAD') }
    }
)
$summary = [ordered]@{
    schema_version = 1; name = $SnapshotName; created_at = [DateTimeOffset]::Now.ToString('o')
    source_commit = Invoke-LocalGit -Directory $repoRoot -GitArguments @('rev-parse', 'HEAD')
    source_branch = Invoke-LocalGit -Directory $repoRoot -GitArguments @('branch', '--show-current')
    source_bundle_sha256 = (Get-FileHash -LiteralPath $bundlePath -Algorithm SHA256).Hash
    installed_dll_sha256 = (Get-FileHash -LiteralPath (Join-Path $GameModDirectory 'MMFreeLyrics.dll') -Algorithm SHA256).Hash
    dependency_versions = $dependencyVersions; archives = $archiveRecords.ToArray()
    verification = 'ARCHIVE SHA256 VERIFIED / GIT BUNDLE VERIFIED'
    privacy = '仅限本地私有保存；运行包含私人配置，禁止公开上传。'
    excluded = @('游戏主程序和完整资料包', '外部 F 盘解包树', '历史构建和回滚备份', '运行日志和 Python 缓存')
}
$summary | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $snapshotRoot 'snapshot.json') -Encoding utf8
Write-Host ('本地快照已完成：' + $snapshotRoot)
Write-Host '恢复包包含私人配置，请勿上传 GitHub；同盘快照还需另存到备份盘。'
