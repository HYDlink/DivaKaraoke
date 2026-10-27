# 当前架构

## 游戏运行层

```text
DivaModLoader → DivaKaraoke.dll
  → Init / D3DInit / OnFrame
  → 已有游戏签名、状态与播放时钟
  → LyricManager / FontManager
  → ImGui / DX11 双轨歌词与设置面板
```

运行层读取 Mod 目录中的 `freelyrics.toml`、SRT、Ruby 与歌手 TSV。旁路缺失时使用明确回退，不从任意邻曲继承状态。字体使用 ImGui 内置 stb 后端。

伴奏管理器控制已有音频声道；OBS 管理器只通过有界快照通知独立 Helper。网络、认证与 OBS 请求留在 Helper 中，不放入游戏帧回调。

## 离线工具层

`export_lyrics.py` 复用已有游戏资料、FarcPack 和 opcode 表，输出项目自有缓存。正文、读音和歌手数据由清单及哈希绑定；先完整预检，再安装。失败保留旧成功结果，用户修改过的文件不被静默覆盖。

`local_environment.py` 只读取有限路径字段。优先级为显式参数、选定本地配置、公开的相对路径缺省；不根据维护者的设备目录识别数据来源。来源清单须与配置中的游戏目录绑定。

`run_local_tools.py` 是日常入口。只有显式选择安装或应用操作才传入安装目标；普通导出不会因为配置里存在 `install_dir` 就写游戏。

## 文档与本地上下文

- `README.md` 和用户指南描述当前如何使用。
- `docs/specs` 描述当前行为约束；架构与持久决策独立维护。
- `docs/STATUS.md`、`PLAN.md`、`CURRENT_HANDOFF.md` 只保存精简的当前状态，不作为追加日志。
- `.local/environment.toml` 与 `.local/agent-notes.md` 保存设备上下文，不提交 Git。
- `docs/archive` 保存去标识的历史研究，按需读取；原始设备记录另存本地历史备份与 Git 历史。

游戏签名、结构体偏移、Hook 和歌词/歌手算法保持独立维护边界。当前公开产品基于第二阶段，不包含后续逐字时间实验。
