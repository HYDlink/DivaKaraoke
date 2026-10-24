# 汇总真实离屏回放数据，初始化上传单列；绝不把回放指标当作游戏帧时间。
[CmdletBinding()]
param(
    # 结果根目录，读取基线/修复版 CSV 并写入验证报告。
    [string]$ResultDirectory = (Join-Path (Split-Path -Parent $PSScriptRoot) 'artifacts\performance-investigation')
)
$ErrorActionPreference = 'Stop'
$replayResults = @()
foreach ($variant in @('baseline', 'fixed')) {
    $replayRows = Import-Csv -LiteralPath (Join-Path $ResultDirectory "$variant-replay\frames.csv")
    foreach ($height in @(1080, 2160)) {
        foreach ($show in @(0, 1)) {
            $replayGroup = @($replayRows | Where-Object { [int]$_.height -eq $height -and [int]$_.show_lyrics -eq $show })
            foreach ($activeOnly in @($false, $true)) {
                $replaySteady = @($replayGroup | Where-Object { [long]$_.time_ms -gt 0 -and (-not $activeOnly -or [int]$_.vertices -gt 0) })
                if (-not $replaySteady.Count) { continue }
                $replayCpu = @($replaySteady | ForEach-Object { [double]$_.cpu_us } | Sort-Object)
                $replayDraw = @($replaySteady | ForEach-Object { [double]$_.draw_us } | Sort-Object)
                $replayResults += @{
                    variant = $variant; height = $height; show_lyrics = $show; visible_frames_only = $activeOnly
                    samples = $replayCpu.Count; mean_cpu_us = ($replayCpu | Measure-Object -Average).Average
                    p50_cpu_us = $replayCpu[[int][Math]::Floor(($replayCpu.Count - 1) * 0.50)]
                    p95_cpu_us = $replayCpu[[int][Math]::Floor(($replayCpu.Count - 1) * 0.95)]
                    p99_cpu_us = $replayCpu[[int][Math]::Floor(($replayCpu.Count - 1) * 0.99)]
                    max_cpu_us = $replayCpu[-1]; p50_draw_us = $replayDraw[[int][Math]::Floor(($replayDraw.Count - 1) * 0.50)]
                    runtime_font_rebuilds = @($replaySteady | Where-Object { [int]$_.font_rebuilt -eq 1 }).Count
                }
            }
        }
    }
}
$replayPixels = @()
foreach ($baselineImage in Get-ChildItem -LiteralPath (Join-Path $ResultDirectory 'baseline-replay') -Filter '*.rgba') {
    $fixedImage = Join-Path $ResultDirectory "fixed-replay\$($baselineImage.Name)"
    $baselineHash = (Get-FileHash -LiteralPath $baselineImage.FullName -Algorithm SHA256).Hash
    $fixedHash = (Get-FileHash -LiteralPath $fixedImage -Algorithm SHA256).Hash
    if ($baselineHash -ne $fixedHash) { throw "实际生产绘制像素不一致：$($baselineImage.Name)" }
    $replayPixels += @{ name = $baselineImage.Name; sha256 = $fixedHash; exact_match = $true }
}
if ($replayPixels.Count -ne 8) { throw '生产绘制对照图片不足8张。' }
$replayReport = @{
    status = 'LOGIC / REPLAY / PIXEL VERIFIED'; workload = '真实PV261的38句SRT/Ruby，硬件DX11，1080p/4K，显示开/关'
    measurement = '两版顺序运行，每帧GPU等待置于计时外；time_ms=0的图集上传初始化不混入稳态统计'
    limitations = '不含真实游戏负载、Present、控制台窗口阻塞或OBS编码；不是游戏帧时间验收或真实卡顿调用栈'
    in_game = 'IN-GAME VERIFICATION REQUIRED'; statistics = $replayResults; pixels = $replayPixels
}
$replayReport | ConvertTo-Json -Depth 7 | Set-Content -LiteralPath (Join-Path $ResultDirectory 'validation.json') -Encoding UTF8
Write-Output '验证通过：8张生产画面逐字节一致，回放稳态统计已保存。'
$replayResults | Where-Object { $_.show_lyrics -eq 1 -and $_.visible_frames_only } |
    ForEach-Object { Write-Output ("版本={0}；高度={1}；CPU中位数={2:N2}微秒；P99={3:N2}微秒；曲内字体重建={4}次。" -f $_.variant,$_.height,$_.p50_cpu_us,$_.p99_cpu_us,$_.runtime_font_rebuilds) }
