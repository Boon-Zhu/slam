# AGENTS.md

本文件为在本仓库中工作的智能体（Codex, DeepseekHarness, Zcode, Claude等）提供指导。回答时尽量使用中文。

## 项目概述

本仓库用于 DOGZILLA S2 的 ROS2 室内建图与定位集成，使用原装 MS200 雷达。在约 15 平方米的可控室内环境中，快速验证版先跑通遥控、采集、建图与保存，交付版补齐定位与完整验证。

## 开发约定

### 共识与规范入口

- 涉及功能边界或架构设计时，阅读 [README.md](README.md) 对应章节；自主探索、自动规划绕行、自主到点导航及任意未知位置全局重定位不属于第一版范围。
- 涉及工程基线、故障处理或版本取舍时，阅读[阶段决议](docs/architecture/interface-baseline-decisions.md)；快速验证版有雷达故障确认后降级操作的特定规则。
- 区分已确认决策、候选组件和待核实能力；方案描述不代表已实现或通过真机验证。
- 编写、修改或审查代码、脚本及配置时，遵循阶段决议中的语言、依赖及检查要求；新增或重命名文件、目录、package 和代码标识符时，遵循[命名规范](docs/standards/naming-conventions.md)，其他代码规范与工具配置仍待落实。
- 新增、迁移或整理文档时，遵循[文档索引](docs/README.md)的目录与维护约定，并同步清单和引用。
- 本文件保持在 100 行以内；模块详细规则在讨论确定后按模块放入 `.codex/rules/`，并在此添加适用场景与文件链接。

### 开发环境与常用操作

- 统一开发目标基线为 Ubuntu 22.04 + ROS2 Humble，不要求宿主系统一致；设备分工与容器方案遵循阶段决议 §2。涉及环境、远程连接或 GitHub 操作时，先读取 `.local/environment.md`；缺失或记录不适用时检查本机，不套用其他设备状态。
- 已授权的 Git 推送优先使用 SSH；先核对实际 push URL，本机 SSH 参数见本地记录，不自动改写永久 remote 或 SSH 配置。
- 创建/更新 PR、查询 issue 和仓库状态优先使用 GitHub CLI（`gh`）；先核实账号及目标仓库。沙箱网络失败不等于凭据失效，应按权限流程重试确认。
- `.local/environment.md` 只记录本机配置、验证日期及限制，不提交 Git，不存储密钥或令牌；本地检查结果不代表机器人已验证，也不授权推送或发布。

### 协作与技能

- 创建分支、提交或合并变更时，遵循 [Git 提交与协作规范](docs/agents/git-workflow.md)；编写或更新 PR 正文时必须使用 `mattpocock-skills:pr`（触发说明：`Use when writing a PR body.`），技能定位与不可用时的处理见该规范。
- GitHub issue tracker 是团队共享的权威记录；`.scratch/<feature>/` 保存本地 Markdown spec 与工作草稿，遵循 [Issue tracker 约定](docs/agents/issue-tracker.md)。
- 使用五个默认 triage 标签，本地 Markdown 复用同一组状态词，见 [Triage labels](docs/agents/triage-labels.md)。
- 领域文档采用根目录 `GLOSSARY.md` 与 `docs/adr/` 的单上下文布局，见 [Domain docs](docs/agents/domain.md)。

## 工程约束

### 部署环境

- 2026-11-02 核实的 Pi 5 开发板为 Debian 12 / arm64 宿主，厂商 `yahboomtechnology/ros-humble:3.8` 容器为 Ubuntu 22.04.4 / Humble / Python 3.10.12；这是版本证据，尚不代表构建或真机运行通过，详见[环境核查报告](docs/report/pi5-image-version-audit-2026-11-02.md)。

### 模块边界与数据通路

| 模块 | 职责 |
| --- | --- |
| A：设备接入与运动接口 | 原装传感器接入、时间戳与坐标系核实、原始反馈、运动与停止接口 |
| B：运动估计、建图与定位 | 里程计方案、建图定位、地图持久化与导出、定位状态 |
| C：遥控与运动保护 | 遥控输入、障碍检查、运动限制、故障停车及原因输出 |
| D：运行流程与集成验证 | 用户交互、机器人环境、启动与模式切换、保存与重启协调、状态汇总、集成验收 |

- 用户指令统一发给 D；运动通路为用户 → D → C → A，未来新增导航指令也必须经过 C。
- B 负责运动估计，A 提供实际可用的数据与反馈；控制指令不能直接视为实际位移，厂商里程计需核实来源与质量。
- D 调用 B 的地图能力，地图逻辑归 B；实时障碍保护归 C，不依赖 B 的全局定位正常。
- 每段 TF 必须有唯一且明确的发布者；通常采用 `map → odom → base_link → 传感器坐标系`，实际链路依设备模型确定。
- 模块依赖与接口责任详见 README 第 6 节；具体话题名、消息类型、调用方式及错误语义尚待确定。

### 其他工程约束入口

- **硬件与部署边界：** 保持原装硬件、传感器安装与底层步态，验收时建图定位运行于树莓派，电脑用于遥控、可视化及离线分析；涉及设备能力、候选组件或参数时，阅读 [README §1、§6.4、§7](README.md)。
- **运行与故障：** 按版本落实模式切换、持续操作、避障、失联停止与恢复、雷达降级及 A 自身失效规则；涉及这些行为时，阅读 [README §2、§5](README.md) 和[阶段决议 §7.2–§7.14、§7.26](docs/architecture/interface-baseline-decisions.md)。
- **地图与重启：** 快速验证版单地图、交付版多地图，保存须完整且位姿绑定地图，固定停靠位重启依赖有效位姿及断电期间未搬动；涉及保存、替换或定位恢复时，阅读 [README §3](README.md) 和[阶段决议 §7.12–§7.14](docs/architecture/interface-baseline-decisions.md)。
- **能力与验收：** 定位与防碰撞分别验收，回放不替代实际运动和停车验证，参数依据实测确定；涉及指标或完成判定时，阅读 [README §4、§7](README.md) 和[阶段决议 §7.16](docs/architecture/interface-baseline-decisions.md)。
