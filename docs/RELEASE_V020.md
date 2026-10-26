# DivaKaraoke v0.2.0

发布基线：`release-v2-singer-20261025`，提交`ee5066b445117d1c28954140dd03ec1e1b5a41b5`。按用户明确选择，保留行级歌手配色，不纳入第三版口型/声学逐字功能。

本次改动限定为独立项目名称、DLL与工程名称、发布文档、第三方许可证、新电脑构建/工具入口、公开包清单，以及首次没有freelyrics.toml时保存配置的最小修复。游戏签名、结构体偏移、Hook和生命周期不改。

保留上游及第二版历史提交，发布分支`codex/release-v0.2.0`映射到新仓库main。原第三版开发分支、未提交改动及本机资料留在原工作区。

隐私检查覆盖全部本地引用可达历史和当前源码；未发现Git/GitHub令牌或私钥。两份旧私有安装归档包含OBS密码，未进入Git，禁止用于公开打包。公开包另做脱敏规则检查，不以此承诺绝对不存在所有类型秘密。

验证结果由本轮完成后追加。构建、装载及离线回归不等于游戏内验收。用户游戏运行时不替换DLL；后续退出后再按备份/哈希约定完成本机部署。

## 本轮已完成验证

- 三个公开子模块均从远端取得固定提交；Release/x64构建成功。
- 独立LoadLibraryW装载通过，D3DInit、Init、OnFrame导出保留。
- 生产歌词C++切歌、Ruby、歌手配色、六首真实样本及62首批量歌手旁路通过。
- 第二版309首歌手扫描/成套哈希、人工标记保护、7首真实歌手回归通过。
- OBS模拟13项、原生会话生命周期、结尾停钟与人工暂停回归通过；未连接实际OBS。
- 新目录缺少freelyrics.toml时首次保存、读取和已有用户字段保留通过。
- 公开源码工作区与全可达历史规则扫描未发现认证值；原目录私有ZIP中的两份OBS密码配置不进入发布。

上述为BUILD / LOGIC / DLL LOAD VERIFIED，干净安装包和克隆构建结果另在最终记录中补充。没有对正在运行的游戏进行部署，重命名DLL的实机验证仍为IN-GAME VERIFICATION REQUIRED。

## 干净获取与安装结果

已从发布提交克隆到全新目录，重新通过公开远端取得三个子模块，未复制原工作区依赖。实际运行通用构建入口成功；新目录从PyPI安装Janome 0.5.0和websocket-client 1.8.0，从Google Fonts固定提交下载字体并校验SHA-256，均通过。

候选公开ZIP在中文与空格的新目录回读全部文件哈希、规则扫描、解压、工具中文帮助、独立随包运行库导入、LoadLibrary及D3DInit/Init/OnFrame导出检查通过。依赖测试目录的示例密码网址已排除，实际运行库及许可证保留。详细安装包凭据以最终输出目录package-verification.json为准。

游戏进程正在运行；本轮没有改动游戏目录，不把磁盘构建视为游戏已经加载。当前游戏中的第三版个人试验数据及设置保持。公开v0.2.0只发布第二版，原第三版分支和未提交改动仍留原开发目录，并另有发布前Git bundle备份。

## GitHub同步

目标：https://github.com/HYDlink/DivaKaraoke 。保留上游origin的禁用推送设置，新增release远端，只推送审核过的main与v0.2.0，不使用mirror或force。

当前Git命令行没有可用GitHub登录，GitHub插件也未连接。可以通过Git Credential Manager设备授权登录，凭据保存在系统中，不写入仓库。登录命令：

```powershell
git credential-manager github login --username HYDlink --device
```

本地发布脚本默认只预检，显式--publish后推送main、保留祖先历史及标签，先创建Release草稿、核对上传附件摘要，再公开。它不删除或覆盖已存在但摘要不同的附件。

```bash
python scripts/publish_github_release.py \
  --release-dir artifacts/public-release-v020
```

实际发布在上述命令追加--publish；若已完成网页授权，可以由助手继续执行。最终是否已公开必须以publication.json和远端实际结果为准，不能把本地ZIP当成GitHub Release已发布。
