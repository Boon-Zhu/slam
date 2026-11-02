Status: needs-triage

约定负责人：`Boon-Zhu`。

# B：选择快速验证版运动估计与建图组件

## Question

评估可复用的原版 Humble 组件与实际输入，优先验证已有成熟能力，不能将厂商算法示例当作实机可运行链路。slam_toolbox、Cartographer 均未最终选定。控制指令不能直接视为实际位移，已有里程计需核实来源与质量。

产出：选型依据、来源与固定版本、输入需求、TF 发布方案、录包验证计划及树莓派部署需求。首次数据到达后反馈具体需要的数据条目；快速验证版保留建图必需的运动估计，但不实现独立已有地图定位来阻塞闭环。

## 共同约束

快速验证版先跑通人工操作、采集、建图、保存；交付版补定位、多地图与完整约定验证。用户→D→C→A；保持厂商硬件与底层步态，上游实现不修改，缺口按最小独立节点/组件自研替换。Ubuntu 22.04 / ROS2 Humble，默认 Python 3.10，按需 C++17。新增依赖自行查冲突，无冲突走 PR，有冲突提交 issue。

本 issue 是研究与方案细化的移交，不代表能力已经实现，也不要求在本轮完成代码。影响共同接口或故障规则的变化由相关模块与 D 确认。A/B/C/D 各自保留模块日志，试运行后交叉核对，D 协调。当前日期未定。

## 共同基线来源

[共同基线决议：版本、模块职责、故障语义与工程约束](https://github.com/Boon-Zhu/slam/issues/3)；[Wayfinder map：模块可独立细化方案的共同基线](https://github.com/Boon-Zhu/slam/issues/2)。本 issue 为独立后续研究，不是 map 的未解决 decision ticket。

Published: https://github.com/Boon-Zhu/slam/issues/6
