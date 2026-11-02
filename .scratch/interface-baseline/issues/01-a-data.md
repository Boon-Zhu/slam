Status: needs-triage

约定负责人：`ZWC-Maker`。 GitHub 当前可分配名单未包含该用户，assignee 字段尚未生效；此处记录团队分工，待成员具备可分配资格后补齐。

# A：核实设备数据并完成首次全量采集方案

## Question

核实 MS200、IMU、运动反馈、已有里程计与 TF 的实际来源、单位、频率、时间戳含义和质量，提出首次采集方案。已提供的 Pi 5 审计确认 Debian 12 宿主、Ubuntu 22.04.4/Humble 容器及 DOGZILLALib 3.1.9 方法存在，未验证实际数据或运动。

产出：实际接口与采集覆盖清单、缺失项、采集/回放步骤与证据；首次采集保留全部实际可获取数据，不预先按猜测裁剪。B/C 按需取用并反馈需求；接口逐项确认，不要求模块停止内部研究等待首包。A 负责机身→传感器 TF，B 负责 odom→机身和 map→odom，D 协调唯一发布。

## 共同约束

快速验证版先跑通人工操作、采集、建图、保存；交付版补定位、多地图与完整约定验证。用户→D→C→A；保持厂商硬件与底层步态，上游实现不修改，缺口按最小独立节点/组件自研替换。Ubuntu 22.04 / ROS2 Humble，默认 Python 3.10，按需 C++17。新增依赖自行查冲突，无冲突走 PR，有冲突提交 issue。

本 issue 是研究与方案细化的移交，不代表能力已经实现，也不要求在本轮完成代码。影响共同接口或故障规则的变化由相关模块与 D 确认。A/B/C/D 各自保留模块日志，试运行后交叉核对，D 协调。当前日期未定。

## 共同基线来源

[共同基线决议：版本、模块职责、故障语义与工程约束](https://github.com/Boon-Zhu/slam/issues/3)；[Wayfinder map：模块可独立细化方案的共同基线](https://github.com/Boon-Zhu/slam/issues/2)。本 issue 为独立后续研究，不是 map 的未解决 decision ticket。

Published: https://github.com/Boon-Zhu/slam/issues/4
