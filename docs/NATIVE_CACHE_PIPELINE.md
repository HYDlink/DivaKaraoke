# 原生歌词缓存流水线

本流水线复用既有 `FarcPack.exe` 和已验证的 Future Tone opcode 表；它不实现 CPK 提取器，也不向运行时增加 hook。资料包由 JSON 清单描述，先生成 JSON/SRT，再逐首核对；任一候选失败时，总控不会部署任何资料包的结果。

## 清单

以 `scripts/native_lyric_sources.example.json` 为模板。每一项必须含 `name`、`cpk`、`extract_dir`、`rom_relative`、`output_dir`、`report`，文本表以 `pv_db`（外部已提取文本表）或 `pv_db_relative`（同一包内文本表）二选一。`reuse_extracted` 为真时直接复用既有解包目录。

运行时读取 `PVxxx.srt`，同目录的 `native-cache-manifest.json` 记录每一首的源缓存和部署位置。

## 一键构建与部署

```powershell
python scripts/build_installed_native_lyric_caches.py \
  --source-manifest F:/DivaLyrics/sources.json \
  --farcpack D:/Work/Projects/VibeCoding/DivaKaraOkeLyrics/MikuMikuLibrary/FarcPack.exe \
  --opcode-db D:/Work/Projects/VibeCoding/DivaKaraOkeLyrics/artifacts/Open-PD-Script-Editor/opcode_db/db.json \
  --lyrics-dir E:/SteamLibrary/steamapps/common/Hatsune Miku Project DIVA Mega Mix Plus/mods/MMFreeLyrics/lyrics \
  --reuse-extracted
```

## 只生成与审计，不部署

```powershell
python scripts/build_installed_native_lyric_caches.py \
  --source-manifest F:/DivaLyrics/sources.json \
  --farcpack D:/Work/Projects/VibeCoding/DivaKaraOkeLyrics/MikuMikuLibrary/FarcPack.exe \
  --opcode-db D:/Work/Projects/VibeCoding/DivaKaraOkeLyrics/artifacts/Open-PD-Script-Editor/opcode_db/db.json \
  --lyrics-dir E:/SteamLibrary/steamapps/common/Hatsune Miku Project DIVA Mega Mix Plus/mods/MMFreeLyrics/lyrics \
  --reuse-extracted \
  --skip-deploy
```

## Charts Pack 覆盖审计

Charts Pack 的 `script_nc` 是谱面而非歌词来源。用其权威 `nc_db.toml` 校验每一首注册歌曲都能映射到已经生成的正式 `PVxxx.srt`；未在 TOML 中注册的孤立 DSC 仅记录为未引用资源，不生成空缓存。

```powershell
python scripts/audit_chart_lyric_coverage.py \
  --chart-root E:/SteamLibrary/steamapps/common/Hatsune Miku Project DIVA Mega Mix Plus/mods/F2nd Charts Pack/rom \
  --chart-map E:/SteamLibrary/steamapps/common/Hatsune Miku Project DIVA Mega Mix Plus/mods/F2nd Charts Pack/rom/nc_db.toml \
  --cache-dir E:/SteamLibrary/steamapps/common/Hatsune Miku Project DIVA Mega Mix Plus/mods/MMFreeLyrics/lyrics \
  --opcode-db artifacts/Open-PD-Script-Editor/opcode_db/db.json \
  --report F:/DivaKaraOkeLyrics/native-caches/f2nd-charts-coverage-report.json
```

当前安装路径可直接使用 `artifacts/installed-native-lyric-sources.json`；它支持 `extracted_rom` 直连来源、`script_dir`、`dsc_format` 和 `include_pv_ids`，用于像 PV010 这样经核验的补充脚本来源。

## 注册歌曲覆盖审计

当新 Mod 已有 `mod_pv_db.txt`、但脚本可能复用其他资料包时，可不猜测目录结构，直接核对其 Normal 注册项与正式缓存：

```powershell
python scripts/audit_mod_song_mapping_coverage.py \
  --pv-db E:/SteamLibrary/steamapps/common/Hatsune Miku Project DIVA Mega Mix Plus/mods/New Song Pack/rom/mod_pv_db.txt \
  --cache-dir E:/SteamLibrary/steamapps/common/Hatsune Miku Project DIVA Mega Mix Plus/mods/MMFreeLyrics/lyrics \
  --report F:/DivaKaraOkeLyrics/native-caches/new-song-pack-coverage-report.json
```

报告会将“含歌词文本且缺正式 SRT”列为失败；没有 `lyric` 文本键的注册项会明确列为无歌词文本，而不会用猜测生成空缓存。
