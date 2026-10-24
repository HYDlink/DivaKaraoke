# PV261《君の体温》伴奏模式残留人声音频证据

日期：2026-10-16。用户反馈在已勾选“伴奏模式 / 关闭人声”时仍有初音歌声。本轮只读复用既有官方提取资源，不重新解包，不修改游戏、DLL或音源。

## 结论

PV261原始OGG虽然声明四声道，但只有第一组立体声有信号，第二组立体声全程严格为零。当前模组按标准分轨布局静音pair 1/3：该文件只含pair 0/1，因此关闭的是原本空白的pair 1；pair 3没有对应源声道。结合用户直接听到歌声的反馈，可确认歌声与伴奏同在pair 0，不能靠当前声道增益单独去除。

改变为静音pair 0会把曲目全部有效音频一起关闭。此曲需要另行获得纯伴奏音源或进行离线音源分离，才能实现真实纯伴奏；本轮没有实施替换或分离。

## 完整解码证据

资源：`F:/DivaKaraOkeLyrics/main-extract/rom_steam/rom/sound/song/pv_261.ogg`。

SHA-256：`9DB28999B9E0BC2DCAEA7823DA52A1B1CB74BAD44E7C19E4BC51E4A7955E545E`。

截图实际加载路径`./rom_steam/rom/sound/song/pv_261.ogg`与已有提取资源相符；本机Mod目录按文件名未发现PV261 OGG或CPK覆盖。

以原始44100 Hz完整解码245.5秒，无混音、重采样或声道重排滤镜。下表使用从1开始的声道编号；代码及JSON索引从0开始。

| 声道 | 每声道采样数 | 非零采样数 | 峰值 | RMS（dBFS） |
| --- | ---: | ---: | ---: | ---: |
| 1 | 10,826,550 | 10,601,024 | 0.637313 | -16.434 |
| 2 | 10,826,550 | 10,593,728 | 0.633562 | -16.227 |
| 3 | 10,826,550 | 0 | 0 | 无，严格静音 |
| 4 | 10,826,550 | 0 | 0 | 无，严格静音 |

对照资源：`F:/DivaKaraOkeLyrics/dlc00-extract/rom_steam_dlc/rom/sound/song/pv_424.ogg`，SHA-256为`01B0D097FF8574AA588E6CE563ABF15FE4163C4EE4074A7250D2BB4E3C2E6236`。同为Vorbis/44100 Hz/四声道，完整168秒中四个声道均存在非零信号；后两个声道RMS分别为-26.004与-27.713 dBFS。该对照证明此次解码统计没有统一丢弃第二组声道，但不把“非零信号”自动解释为人声识别。

完整机器可读数据：[channel-audit.json](../../artifacts/pv261-audio-audit/channel-audit.json)。

## 与运行时状态的关系

`Source/managers/non_vocal_manager.cpp`的`ApplyLocked`向pair 1/3请求零增益后直接设置`applied = enabled`；`IsNonVocalApplied`读取此旗标，没有测量原始音轨或实际扬声器输出。因此PV261日志中的“人声静音=1”和录像文件的Off Vocal后缀均只能证明模组静音请求状态。

已有ReDIVA读取器资料将相邻两个原始声道装入一个`channel_pair`；当前四声道文件对应两个源声道对。原已验证游戏上层增益将逻辑pair 1镜像到pair 3，模组延续此控制约定。本轮没有改变签名、偏移或Hook。

音频源结构为 **ANALYSIS VERIFIED**；结论绑定此源文件及用户听感反馈，不扩展为全曲库声部判断或全局Hook验收。

## 复查命令

依赖Python 3、NumPy以及PATH中的ffmpeg/ffprobe。以下在项目根目录通过Git Bash执行，按用户约定用反斜杠分行；PowerShell执行时将行尾反斜杠改为反引号。

```bash
python scripts/audit_non_vocal_audio.py \
  --audio "F:/DivaKaraOkeLyrics/main-extract/rom_steam/rom/sound/song/pv_261.ogg" \
  --audio "F:/DivaKaraOkeLyrics/dlc00-extract/rom_steam_dlc/rom/sound/song/pv_424.ogg" \
  --output "artifacts/pv261-audio-audit/channel-audit.json"
```
