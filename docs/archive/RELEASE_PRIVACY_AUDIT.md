> 历史研发资料，仅供追溯，不是当前操作指南。设备绝对路径已去标识；原始记录保留在私有历史备份及 Git 历史。

# 公开发布隐私检查（2026-10-26）

## 实际检查

原开发仓库全部本地引用可达历史的567个唯一文件对象、提交/标签元数据及当前源码/本机Git配置执行只读规则扫描。未命中GitHub Token、常见API密钥、私钥、带密码的远程地址或非空认证字段。当前发布工作区增加文件后再次扫描，亦未发现认证值。该结论是规则扫描结果，不是对任意编码、任意秘密的绝对保证。

普通公开clone不会把本机系统凭据管理器中的Git/GitHub登录信息写入提交。正常Git历史仍包含作者姓名、邮箱和开发文档的本机路径；本次没有删除这些署名或改写历史。

## 已定位且排除的本地内容

原artifacts/local-snapshots下两份installed-mod-private.zip的tools/obs-helper.json各有非空OBS密码。它们是本地恢复包中的同类配置，未进入Git。检查只在内存中识别字段，报告不含原文。它们不能原样上传，公开包只收录password为空的obs-helper.example.json。

三个本机私有恢复ZIP未删除、未上传；游戏原始资产、商业字体、用户配置和本机依赖环境不作为公开打包来源。公开包白名单单独定义于scripts/package_public_release.py，不会把整个artifacts或游戏目录压缩上传。随包库中的第三方单元测试示例认证网址已通过排除非运行必需的tests目录避免混入安装包，源许可证保留。

## 可重复检查

下面使用Git Bash多行语法；PowerShell/CMD可合并成一行：

```bash
python scripts/audit_release_privacy.py \
  --output artifacts/release-checks/privacy.json
```

该脚本只输出规则、路径、行号和必要长度，不输出认证值。不会读取Windows凭据管理器。公开ZIP使用verify_public_package.py单独扫描全部条目、验证清单哈希并检查工具与DLL。
