Status: needs-triage

约定负责人：`zer0-2w`。 GitHub 当前可分配名单未包含该用户，assignee 字段尚未生效；此处记录团队分工，待成员具备可分配资格后补齐。

# D：落实机器人环境与开发 CI 最小试运行方案

## Question

D 管理机器人运行环境并保留厂商系统；PC1 为 WSL2 Ubuntu 26.04 + Ubuntu 22.04/Humble Docker，PC2 原生 Ubuntu 22.04/Humble。实际 Pi 5 容器 Python 3.10.12、GCC11.4、CMake3.22.1、colcon0.16；本地镜像 ID 不等于可拉取的远端 digest，RepoDigests 为空。

产出：镜像/依赖固定与复现方案、兼容性记录、统一本地/CI 检查入口。选定 Ruff+mypy+pytest，具体版本及 ROS 插件兼容性需测试；不要覆盖厂商 pytest6.2.5 来强行对齐检查工具。PR 门槛为格式、静态分析、类型、必要构建及无硬件测试。GitHub Actions 暂定采用，最小试运行须验证正常通过、故意真实错误失败、日志可定位、开发容器可复现。C++ 实际引入时补适用检查。

各模块维护自身参数，D 加载配置组合，参数只有一个权威定义。数据处理 ROS 时间，回放统一播放时间，真机超时单调计时。代码规范 docs/Standard/coding-standard.md 当前缺失，应据已定基线补齐适用细则。

## 共同约束

快速验证版先跑通人工操作、采集、建图、保存；交付版补定位、多地图与完整约定验证。用户→D→C→A；保持厂商硬件与底层步态，上游实现不修改，缺口按最小独立节点/组件自研替换。Ubuntu 22.04 / ROS2 Humble，默认 Python 3.10，按需 C++17。新增依赖自行查冲突，无冲突走 PR，有冲突提交 issue。

本 issue 是研究与方案细化的移交，不代表能力已经实现，也不要求在本轮完成代码。影响共同接口或故障规则的变化由相关模块与 D 确认。A/B/C/D 各自保留模块日志，试运行后交叉核对，D 协调。当前日期未定。

## 共同基线来源

[共同基线决议：版本、模块职责、故障语义与工程约束](https://github.com/Boon-Zhu/slam/issues/3)；[Wayfinder map：模块可独立细化方案的共同基线](https://github.com/Boon-Zhu/slam/issues/2)。本 issue 为独立后续研究，不是 map 的未解决 decision ticket。

Published: https://github.com/Boon-Zhu/slam/issues/10
