# 文档索引

本页用于查找仓库文档和确定新增文档的位置。项目需求与顶层架构从根目录 [README.md](../README.md) 开始；领域术语见 [GLOSSARY.md](../GLOSSARY.md)。

## 目录结构

```text
docs/
├── README.md       # 文档索引与维护约定
├── architecture/   # 跨模块架构与共同工程基线
├── adr/            # 有编号的单项架构决策及取舍理由
├── standards/      # 命名等工程规范
├── development/    # 开发环境配置与日常开发指南
├── report/         # 调查、评估与实际检查记录
└── agents/         # Agent 工作流程与协作约定
```

`architecture/` 说明共同遵循什么基线，`adr/` 记录特定决策的背景与代价，`report/` 提供调查证据和评估。报告中的建议、估算或候选能力不自动成为已确认决策，也不代表实现或真机验收完成。

## 文档清单

### architecture：共同基线

| 文档 | 内容简介 |
| --- | --- |
| [interface-baseline-decisions.md](architecture/interface-baseline-decisions.md) | 接口责任、技术栈、人员分工、版本范围、运动与故障行为、开发环境和 CI 的阶段决议，以及待核实事项。 |

### adr：单项架构决策

| 文档 | 内容简介 |
| --- | --- |
| [0001-module-boundaries-and-motion-path.md](adr/0001-module-boundaries-and-motion-path.md) | A/B/C/D 职责和 D→C→A 运动通路的决策理由。 |
| [0002-unmodified-upstream-and-component-replacement.md](adr/0002-unmodified-upstream-and-component-replacement.md) | 保持上游原样、以最小独立组件补足缺口的边界与代价。 |
| [0003-rapid-validation-fault-tradeoffs.md](adr/0003-rapid-validation-fault-tradeoffs.md) | 快速验证版的故障处理取舍及尚未覆盖的验证范围。 |

### standards：工程规范

| 文档 | 内容简介 |
| --- | --- |
| [naming-conventions.md](standards/naming-conventions.md) | 文件、目录、package、函数、私有方法、类型、配置与测试的命名规则及兼容例外。 |

### development：开发指南

| 文档 | 内容简介 |
| --- | --- |
| [windows-setup.md](development/windows-setup.md) | 面向全新 Windows 环境的 WSL2 Ubuntu 22.04、Humble、Python、GitHub CLI 与 SSH 安装、自检和使用指南。 |
| [device-capture-entry.md](development/device-capture-entry.md) | 首次采集 ROS 控制与反馈入口的构建、mock、真机接管前提、命令、原始反馈及关闭审计语义。 |

### report：调查与评估

| 文档 | 内容简介 |
| --- | --- |
| [device-capture-entry-acceptance-2026-11-08.md](report/device-capture-entry-acceptance-2026-11-08.md) | ROS 入口实现与独立审查闭环，Humble 构建、80 项测试及模拟 bag 录制回放验收；真机部署仍待验证。 |
| [device-capture-readonly-verification-2026-11-09.md](report/device-capture-readonly-verification-2026-11-09.md) | ROS 入口 arm64 构建与真机只读反馈、部署权限修正、实际频率、串口排他及退出释放验证；未运动或正式全量采集。 |
| [device-first-capture-verification-2026-11-08.md](report/device-first-capture-verification-2026-11-08.md) | 首次采集方案实机复核：IMU/关节/电池有效返回、相机去盖复查、雷达退出异常、磁盘/时钟及资源交接。 |
| [device-first-capture-investigation-2026-11-06.md](report/device-first-capture-investigation-2026-11-06.md) | issue #4 首次全量采集前置调查：实机资源与录包工具、APP 数据覆盖缺口、方案决策与试采门槛。 |
| [pstack-assessment-2026-11-06.md](report/pstack-assessment-2026-11-06.md) | pstack 官方工作流、宿主依赖、与现有协作规范的冲突，以及有限自动编码试点建议；未安装或运行。 |
| [dogzilla-system-audit-2026-11-05.md](report/dogzilla-system-audit-2026-11-05.md) | 实机系统分层、开机服务、28 个厂商包及依赖、A/B/C/D 接入边界；MS200 数据实测与退出异常。 |
| [dogzilla-interface-audit-2026-11-05.md](report/dogzilla-interface-audit-2026-11-05.md) | 雷达、运动、IMU、关节和 TF 的源码接口、单位、时间、QoS、失败语义与证据哈希。 |
| [pi5-image-version-audit-2026-11-02.md](report/pi5-image-version-audit-2026-11-02.md) | Pi 5 宿主与厂商 Humble 镜像版本；补充 SSH 登录、无线连接检查、2026-11-05 一次短时前进与正常停止实测，以及断线和未验证范围。 |
| [upstream-policy-assessment.md](report/upstream-policy-assessment.md) | 未修改上游策略的工作量汇总、估算前提和扩大替换范围的边界。 |
| [upstream-policy-device.md](report/upstream-policy-device.md) | A 设备接入与运动适配的上游复用、自研替代成本及待验证项。 |
| [upstream-policy-mapping.md](report/upstream-policy-mapping.md) | B 运动估计、建图与地图业务的复用范围、可行性与工作量。 |
| [upstream-policy-protection-integration.md](report/upstream-policy-protection-integration.md) | C 运动保护与 D 运行集成的业务缺口、工作量及验证成本。 |

### agents：协作流程

| 文档 | 内容简介 |
| --- | --- |
| [domain.md](agents/domain.md) | 领域术语、单上下文布局、ADR 冲突处理和架构入口约定。 |
| [git-workflow.md](agents/git-workflow.md) | 分支、提交、PR 与合并规则，以及 PR skill 的使用要求。 |
| [issue-tracker.md](agents/issue-tracker.md) | GitHub issue 权威记录、本地 Markdown 草稿及 Wayfinding operations。 |
| [triage-labels.md](agents/triage-labels.md) | 五种 triage role 与 GitHub label、本地状态词的映射。 |

## 文档维护约定

1. 新增文档时按上述用途选目录，按[命名规范](standards/naming-conventions.md)命名，并在本页对应清单加入文件名、链接和简介。只有出现实际内容需求时才新增目录。
2. 持续维护文档使用稳定主题名；需要保留每次检查证据的快照使用日期后缀。正文明确日期、适用范围，以及已确认、建议、待验证的区别。
3. 文档链接使用相对于当前文件的路径；重命名或迁移时同步本页、根 README、AGENTS 和仓库内其他引用，检查文件目标与章节锚点。历史证据时间与结论范围保持原义。
4. ADR 继续按编号独立存放在 `adr/`，不并入阶段决议。领域概念统一引用根目录 GLOSSARY，避免在多处维护冲突定义。
5. `.scratch/<feature>/` 保留本地 spec 与工作草稿，不纳入正式文档清单；团队共享记录按 [issue tracker 约定](agents/issue-tracker.md)维护。迁移本地文档不表示已同步 GitHub。
6. 调整目录或索引后，检查清单是否覆盖 `docs/` 下全部正式文档，并检查仓库内旧路径引用与相对链接。此类检查不替代软件构建或真机验收。
7. `.local/environment.md` 保存本机环境、连接方式与检查状态，由 `.gitignore` 排除，不纳入正式文档清单。共用环境基线仍以阶段决议 §2 为准，常用操作优先项见根目录 AGENTS；本机记录不保存私钥或令牌。
