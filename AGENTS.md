# 开发协作指南

## 启动流程

每次开发会话开始时，依次执行：

1. 阅读 `docs/STATUS.md`。
2. 阅读 `docs/PLAN.md`。
3. 阅读与当前任务相关的 `docs/ARCHITECTURE.md` 章节。
4. 进行架构或产品决策时阅读 `docs/DECISIONS.md`。
5. 仅在需要历史证据时阅读 `docs/research/` 下的研究文档。
6. 检查 `git status`。

## 当前交接：原版原生歌词 M0（最高优先级）

完成启动流程后，必须阅读 `docs/CURRENT_HANDOFF.md`。该文件是当前工作的权威交接入口；若它与较早的研究笔记表述不同，以该文件为准。

原版基础包数据 M0 已用 PV276 完成 **LOGIC VERIFIED**：`pv_276_normal.dsc` 的完整 `TIME + LYRIC ID` 序列已与 `pv_276.lyric.001–050` 对应。用户的实际目标 PV424 属于官方 DLC：其文本在 `diva_dlc00_region/.../mdata_pv_db.txt`，且该表指向 `pv_424_{easy,normal,hard,extreme}.dsc`。下一项最小任务是用已有 FARC Pack/MM+ CPK 提取能力从 DLC CPK 定向提取 PV424 的 DSC；不得自行写 CPK 提取器。详细证据见 `docs/research/pv276-native-lyric-evidence.md`。

不得自行实现 CPK 提取器、猜测二进制 `pv_db` 或从零写 DSC opcode parser；不得把 X Song Pack、F2nd 或其 `mod_pv_db` 作为主验证路径；不得做全曲扫描、通用数据库框架、运行时新 hook、正式 KTV 或 SRT 扩展。仅 PV424 官方 DLC 资料已获准进入当前范围；外部 SRT 只保留为后备。

## 本机游戏路径

用于本机构建产物部署、原始 Mod 加载验证和后续游戏内验证的 Project DIVA Mega Mix+ 安装目录为：

`E:\SteamLibrary\steamapps\common\Hatsune Miku Project DIVA Mega Mix Plus`

除非任务明确要求部署、运行或验证，否则不要写入该目录。

## 开发规则

始终选择可独立验证的最小任务。优先顺序为：逻辑测试 → 预览/调试验证 → 游戏集成验证，而不是立即进行完整游戏测试。

## 完成定义

代码写完不等于完成。任务只有在适当的验证通过后才能标记为完成；无法验证时必须明确标记为 `NOT VERIFIED` 或 `IN-GAME VERIFICATION REQUIRED`。

## 文档更新

每个有意义的任务结束后，必须更新 `docs/STATUS.md` 与 `docs/PLAN.md`。仅在当前系统结构变化时更新 `docs/ARCHITECTURE.md`；仅在形成持久决策时更新 `docs/DECISIONS.md`。不要把 DECISIONS 当作变更日志，也不要修改历史研究文档以迁就后续架构。

## 安全边界

实现 KTV 呈现行为时，不得随意修改逆向游戏集成层。签名、结构体偏移、hooks 与 DivaModLoader 生命周期的变更必须有明确原因。

## 游戏内验收部署约定（2026-10-10）

用户已明确授权：凡交付需要游戏内验收的 Mod 修改，主编排必须完成统一构建、打包、备份旧 DLL、直接替换本机游戏目录中的对应 DLL，并核对部署文件与构建产物的 SHA-256 一致，之后再通知用户测试。不得只交付压缩包或要求用户自行替换 DLL；无需重复询问部署许可。配套工具和依赖也应同步安装，保留用户已有配置、歌词和字体。子代理只负责子任务，最终整合与部署由主编排完成。

部署前检查游戏是否运行；正在运行时不得把磁盘替换当作当前进程已加载新版，不擅自强制结束游戏。应明确告知需要退出游戏，并在退出后继续完成部署。游戏内听感及录像效果仍由用户实际验收，部署成功不等于游戏内验证通过。
