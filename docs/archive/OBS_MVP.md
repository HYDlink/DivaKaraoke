> 历史研发资料，仅供追溯，不是当前操作指南。设备绝对路径已去标识；原始记录保留在私有历史备份及 Git 历史。

# OBS 自动录制 MVP

DLL 后台 Named Pipe → 独立 Python Helper → 本机 OBS WebSocket 5。默认关闭，仅 PV 鉴赏自动录制。帧线程不执行网络或认证。

## 用户验收

OBS 启用 WebSocket（默认 4455），准备游戏捕获、音轨、输出路径。复制 tools/obs-helper.example.json 为同目录 obs-helper.json，填写密码，然后运行：

```text
python tools/obs_helper.py
```

Ctrl+G 的 PV 工具面板测试连接，启用联动与自动录制，保存到独立 obs-tools.toml。开始 PV 应录像，暂停继续录制，返回选曲停止；下一首产生新文件。检查提前退出、关闭开关、游戏退出、已有人工录制和 OBS 断线。

开始依据：PV POST PROCESS TASK 准备、PVID、鉴赏模式、isPlaying 与时钟递增。结束依据：PVsel 或离开鉴赏模式。暂停和歌词末句不作为结束。游戏异常退出后八秒无心跳，尽力停止本功能仍拥有的录制。

自然结束事件、首尾帧、实际输出质量为 IN-GAME VERIFICATION REQUIRED。MVP 不预热，可能缺开头或保留尾部过渡；驻留结束画面不发 PVsel 时需定位明确结束事件。暂停菜单也会录入。

已有录像跳过，StartRecord 成功响应才认领。人工停止/重启、断线重连释放所有权，同 PV 不重启。启动响应丢失不重试或停止未知录像，提示在 OBS 检查。OBS 无原子所有权接口，其他控制器同时操作仍存在瞬间竞争。Ctrl+C 尽力收尾，强杀 Helper 或断线不能保证停止。

## 接线和测试

ObsManager_Inst 是 lazy 实例；Init()/OnGameState(const char*)/OnFrame()/OnImGUI()，UI 由调用方窗口包裹。生命周期与快照分别加锁，后台每秒心跳。本项目不支持 DLL 热卸载。

附带 tools/obs_runtime 的 websocket-client 1.8.0 和 Apache-2.0 许可证；Python 3.9+。缺依赖时：

```text
python -m pip install \
  --target tools/obs_runtime \
  --requirement tools/obs-requirements.txt
```

自定义配置：

```text
python tools/obs_helper.py \
  --config tools/obs-helper.json
```

反斜杠是分行展示；PowerShell 执行时用反引号或合并一行。模拟测试：

```text
python scripts/test_obs_helper.py
```

七项模拟测试含真实 Windows Named Pipe 对接模拟 OBS，不连接真实 OBS、不录像。协议依据：[OBS 官方协议](https://github.com/obsproject/obs-websocket/blob/master/docs/generated/protocol.md)。状态 LOGIC VERIFIED；整体 DLL 构建由主代理确认；游戏录像待用户验收。

