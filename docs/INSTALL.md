# 安装与升级

需要Microsoft Visual C++ 2015–2022 x64运行库（https://aka.ms/vs/17/release/vc_redist.x64.exe）。适用Windows x64版Project DIVA Mega Mix+及DivaModLoader。v0.2.0使用2026-10-25第二阶段冻结基线，包含双轨KTV、Ruby日文注音、歌手配色、伴奏和OBS辅助，不包含逐字时间算法。

## 普通玩家

1. 先安装[DivaModLoader](https://github.com/blueskythlikesclouds/DivaModLoader)。
2. 将Release安装ZIP里的`DivaKaraoke`文件夹解压到游戏`mods`目录。
3. 若游戏根`config.toml`有`priority`白名单，加入`DivaKaraoke`。
4. 旧`MMFreeLyrics`目录先备份，再设置其`config.toml`的`enabled=false`，确保只启用一个版本。不要同时加载两份DLL。
5. 新包保留`freelyrics.toml`设置文件名。迁移旧用户时，复制旧`freelyrics.toml`、`singer-colors.toml`、`audio-tools.toml`、`obs-tools.toml`及自有`lyrics`/`fonts`。字体路径可能需要在Ctrl+F中重选。不要用新包覆盖自己的配置。

公开包附带Noto Sans JP及其OFL许可证，不含本机商业字体、OBS密码、游戏音视频、CPK、原始DSC或完整文本数据库。歌词缓存从用户自己的游戏/曲包生成，或迁移自己的既有缓存；本项目代码许可证不授予歌曲资源版权。没有时间线时只显示游戏触发的当前句，不会假造下一句。

## 歌词与注音工具

游戏DLL无需Python。离线导出和OBS助手需要Python 3.11或更新版本。源码用户运行`tools\setup_python_tools.cmd`安装固定版本Janome及websocket-client；发行包已包含这两个运行库。

复用已有FarcPack/MM+ CPK提取结果，不自行实现CPK解析器。第三方工具来源见`THIRD_PARTY_NOTICES.md`。准备`MikuMikuLibrary/FarcPack.exe`及`artifacts/Open-PD-Script-Editor/opcode_db/db.json`，或通过对应参数指定。官方提取目录应包含`diva_main`、`diva_main_region`以及已拥有DLC对应目录。提取方法及来源映射见`LYRICS_EXPORTER_MVP.md`、`EXTRACTED_ASSET_REUSE.md`，其中E/F盘路径只是开发历史记录，不能直接照抄。

下面多行命令使用Git Bash语法；PowerShell/CMD可把整段写成一行：

```bash
python scripts/export_lyrics.py \
  --game-dir "D:/SteamLibrary/steamapps/common/Hatsune Miku Project DIVA Mega Mix Plus" \
  --extracted-root "D:/DivaAssets" \
  --farcpack "D:/Tools/MikuMikuLibrary/FarcPack.exe" \
  --opcode-db "D:/Tools/Open-PD-Script-Editor/opcode_db/db.json" \
  --output-dir artifacts/exported-lyrics \
  --install-dir "D:/SteamLibrary/steamapps/common/Hatsune Miku Project DIVA Mega Mix Plus/mods/DivaKaraoke/lyrics"
```

高级曲包映射使用`--source-manifest`，相对路径以清单目录为基准。导出器保护用户手改文件，发现冲突会拒绝整批覆盖。歌手活动只是推测，剧情无声口型等例外仍需人工标记。

## OBS与伴奏

在OBS启用WebSocket服务，复制`tools/obs-helper.example.json`为`tools/obs-helper.json`，填写本机OBS密码，再启动`tools/start_obs_helper.cmd`。密码只保存在你的电脑，不提交Git。录制行为见`OBS_CONNECTOR.md`；伴奏支持范围见`NON_VOCAL_SUPPORT.md`。

Ctrl+F字体、Ctrl+G歌词及工具、Ctrl+S保存、Ctrl+L读取配置。声音与录制最终效果必须在实际游戏和OBS中验收。
