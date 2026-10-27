# 常见问题

| 问题 | 先检查什么 |
| --- | --- |
| Ctrl+F / Ctrl+G 打不开 | DML是否启用、Mod是否加载、目录是否多套一层 |
| 没有双轨歌词 | `lyrics`中是否有当前PVID的SRT；没有时间线时只有原生当前句回退 |
| 日文成方框 | 在Ctrl+F重新选含日文字形的字体并保存 |
| 没有注音或歌手颜色 | 同曲的 `.ruby.tsv` / `.singers.tsv` 是否存在并匹配SRT |
| 伴奏模式仍有人声 | 音源可能没有独立人声轨，见[伴奏说明](NON_VOCAL_SUPPORT.md) |
| OBS连不上或不录制 | 按[OBS说明](OBS_CONNECTOR.md)检查Helper、端口、密码和两个录制开关 |
| 工具找不到目录 | 检查自己的 `.local/environment.toml`，不要使用别人的目录 |

仍有问题时，提供版本、PVID、操作步骤和报错。不要附密码、Token或整份私人配置。
