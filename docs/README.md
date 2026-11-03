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

### report：调查与评估

| 文档 | 内容简介 |
| --- | --- |
| [pi5-image-version-audit-2026-11-02.md](report/pi5-image-version-audit-2026-11-02.md) | 2026-11-02 实际读取的 Pi 5 宿主、厂商 Humble 容器及软件版本；不代表运动或组件运行已验证。 |
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
