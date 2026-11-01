# 系统组织形式调研与原型（待讨论）

日期：2026-11-01。用途：回答“我们的代码如何分包、节点在哪里运行、模块怎样通信与协同启动”，为 README §9.1 的接口讨论提供具体对象。采用 `prototype` skill 的逻辑原型分支。

**这是候选结构，不是接口 spec、生产实现或真机验证结果。** 双击同目录 `prototype.html` 即可查看并交互，无网络、安装或 ROS 环境要求。原型内所有数据只存在内存，刷新即重置。

## 依据与边界

已读取当前 README、AGENTS.md、会话决定。AGENTS 引用的 `docs/Standard/coding-standard.md` 当前不存在，未找到替代代码规范；因此仅遵循现有项目约束及 prototype 最小实现要求。

已确认：A 由 4 负责，B 由 Boon-Zhu（3）负责，C 由 NeuviFuri1115（1）负责，D 由 2 负责；允许互助。目标为 Ubuntu 22.04 + ROS2 Humble，Python 默认且严格检查，必要时 C++，colcon 构建、ament_python / ament_cmake 分包。电脑 1 使用容器；电脑 2 原生 Ubuntu；机器人保留厂商环境，兼容性待核实。所有真机 ROS 节点集中在机器人运行，电脑先通过 SSH 操作和获取录包。跨设备 ROS 通信不是开工条件。

已确认的行为：运动输入经过 C 再到 A；B 的定位失败不应阻断正常的受保护遥控；建图/定位互斥；地图替换成功使旧停靠位绑定失效；故障恢复不重放旧指令。

以下包名、节点名、接口名、节点进程拆分和启动协调方案均为本次提案；没有获得用户确认。

## 具体组织提案

四个职责不等于四个进程，也不必恰好四个 ROS package。建议先以少量职责明确的包组织自己的代码，外部算法与厂商驱动尽量作为依赖复用。

```text
workspace/                         # 两台电脑各有自己的副本
  src/
    dogzilla_device/               # A，ament_python；设备适配，底层调用
      device_adapter.py            # 候选 node：protected_motion → 厂商控制接口
      launch/ config/              # 驱动配置、静态 TF / 机器人模型接入
    dogzilla_mapping/              # B，ament_python；集成而非重写 SLAM
      mapping_manager.py           # 地图事务、初始位姿绑定、状态归一
      launch/ config/              # 建图 / 定位分别启动上游组件
    dogzilla_protection/           # C，ament_python
      teleop_input.py              # 输入转换；具体输入来源待定
      motion_guard.py              # 新鲜度、障碍方向限制、故障原因
      protection_logic.py          # 不依赖 ROS 的纯逻辑，便于离线测试
    dogzilla_bringup/              # D，ament_python
      runtime_coordinator.py       # 模式切换、就绪协调、状态汇总
      launch/                      # robot / mapping / localization / replay
    dogzilla_interfaces/           # 仅确需自定义消息时创建；ament_cmake
      msg/ srv/ action/            # 共同维护；不可先填满无用接口
  build/ install/ log/             # 自动生成，不是代码源文件
```

`package` 是构建和分发单元；`node` 是运行时职责单元；`process` 是操作系统进程。原型暂按自研 node 独立进程解释，实际可以调整，不要求厂商或上游按此方式重组。纯逻辑文件并不是额外 ROS node。

### 运行位置

| 环境 | 运行内容 | 明确限制 |
| --- | --- | --- |
| 电脑 1 容器 | 编写代码、检查、录包回放及 B/C 离线验证 | 回放路径不启动真实运动适配器，不向机器人发运动指令 |
| 电脑 2 原生 Ubuntu | 同一代码构建检查、SSH 运维、获取录包 | 首阶段不要求电脑 ROS graph 接入机器人 |
| 机器人厂商系统 | A 驱动/适配、B 算法与地图管理、C 保护、D 协调，以及录包 | 实际 ROS 版本、CPU 架构与资源未核实，不能直接复制电脑构建产物 |

电脑上的 SSH 会话只是操作入口，不等于遥控安全协议。输入端断开检测、指令有效期、A 收不到 C 输出时的兜底停车是必须明确的问题，不能仅依靠 SSH 或进程退出。

### 通信与责任候选

| 通路 | 建议形式 | 内容与未决点 |
| --- | --- | --- |
| A → B/C：扫描 | topic，优先复用 `sensor_msgs/msg/LaserScan` | 名称可 remap；frame、时间戳、QoS、频率需核实 |
| A → B：IMU / 反馈 | topic，仅实际存在时接入 | 不假定有可信 odom，不以指令积分充当测量 |
| 输入 → C → A：运动 | 两条分离的 topic：原始输入、受保护输出 | 消息需表达运动分量与新鲜度；`Twist` / `TwistStamped` / 自定义接口待评估，不先固定 |
| A/B/C → D：状态 | topic | 不仅一个 ok 布尔值；需能区分就绪、数据过期、限制、故障和原因 |
| D → B：保存/加载 | 短请求可用 service；长任务需反馈/取消则考虑 action | 不把收到请求当作完成；地图完整保存、替换与绑定更新由 B 负责 |
| D → C/A：模式切换停车协调 | 具体接口待决定 | 请求停车后需要可观察的完成条件；成功后再停旧 B 模式、启动新模式 |
| B/A → 使用者：TF | TF 数据通路 | 见下表；每条边只能有一个发布者 |

以上 transport 选择依据 ROS2 官方对 topic/service/action 的语义，而非当前设备已有接口的描述。连续数据用 topic，快速请求响应用 service，需要进度反馈与取消的长任务用 action。[1][2][3]

### TF 与时间

| TF 边（示意） | 责任 | 发布者选择 |
| --- | --- | --- |
| map → odom | B | 当前唯一激活的建图或定位组件 |
| odom → base_link | B | 经核实的厂商估计或 B 的估计器，不能两者同时发布 |
| base_link → laser | A | 经核实的固定外参 / 模型发布者，实际 frame 名待查 |

额外 base_footprint 等 frame 以设备模型为准。实时运行和回放采用不同时间配置；回放时相关节点要一致使用录包时钟。指令超时与模式切换不能仅凭 UI 显示时间实现；计时语义另需设计。

### 启动与切换候选

1. D 的 launch 组织启动配置；A/C 启动时默认不输出非零运动。
2. 驱动与 TF 可用后，D 根据数据与状态确认就绪，而不是等待固定秒数。
3. D 启动选定的 B 模式。C 的保护链不以全局定位成功为前提。
4. 模式切换：停运动并确认 → 停旧模式 → 启动新模式 → 验证就绪 → 等待新的遥控指令。
5. 回放使用专门入口，以录包替换设备输入，并断开真实执行链。

launch 可以描述节点、参数、remap 和进程启动，但进程启动并不等于数据就绪；业务层的有效性与切换完成条件仍由项目定义。[4]

## 对候选上游组件的观察

- `slam_toolbox` Humble 分支提供建图、定位与地图/位姿图保存相关能力；栅格地图与序列化位姿图不是同一种持久化产物。最终定位方案会影响 B 必须保存什么，不能先把保存接口简化成“写一个图片文件”。[5]
- 该分支示例配置包含 `odom_frame`、`map_frame`、`base_frame`、`scan_topic` 与模式项，说明可以通过配置接入已有 graph；示例值不是我们机器的实测值，不能照抄保护阈值或 frame 名。[6]
- Yahboom 当前公开 README 描述 ROS2 Humble、Python 与多种遥控方式，但不能证明本机固件/驱动版本、反馈话题、停止响应或里程计质量。此次未审计厂商全部源码，没有真机连接。[7]

## 原型交互与简化

页面展示三个部署位置、候选包/节点、运动及观测通路、当前模拟状态；可以自由操作，也可以按场景步骤演练。

- 停车、节点就绪、定位有效性均由点击模拟，不是实际测量。
- 故障按钮代表已检测到失效，没有模拟超时阈值、传输延迟、机身轮廓或真实碰撞几何。
- 障碍只抽象为“当前请求方向是否可通行”；不据此推断转身或退开安全。
- 地图保存与位姿绑定仅模拟规则，既不写盘也不产生真实地图。
- 地图场景从无地图开始，演练需先保存地图并记录有效停靠位；不能把截图当作系统实现证据。
- 自由操作偏离引导流程时，重新点场景标签重置。关闭页面丢失所有状态。

## 通过原型需要讨论的下一问题

建议先评审：**是否接受“职责分包 + 可复用上游组件 + 机器人集中运行 + 独立回放入口”这一具体骨架？** 然后逐项确定运动输入来源、A 的停止保障、B 的估计来源、D 的就绪条件。Q13 尚未决定；无需强行一次决定全部 ROS topic 名称。

尚待核实/决策：机器系统与版本；厂商启动图与遥控旁路；传感器/反馈/TF；A 的停止与输出丢失保护；速度表达和时效；ROS QoS；B 算法与地图文件格式；模式切换失败恢复；定位有效性判据；测试和 CI 工具具体配置。

## 一手来源

1. [ROS2 Humble Topics 官方文档源](https://raw.githubusercontent.com/ros2/ros2_documentation/humble/source/Concepts/Basic/About-Topics.rst)
2. [ROS2 Humble Services 官方文档源](https://raw.githubusercontent.com/ros2/ros2_documentation/humble/source/Concepts/Basic/About-Services.rst)
3. [ROS2 Humble Actions 官方文档源](https://raw.githubusercontent.com/ros2/ros2_documentation/humble/source/Concepts/Basic/About-Actions.rst)
4. [ROS2 Humble Launch 官方教程源](https://raw.githubusercontent.com/ros2/ros2_documentation/humble/source/Tutorials/Intermediate/Launch/Creating-Launch-Files.rst)
5. [slam_toolbox Humble README](https://github.com/SteveMacenski/slam_toolbox/blob/humble/README.md)
6. [slam_toolbox Humble 建图配置](https://github.com/SteveMacenski/slam_toolbox/blob/humble/config/mapper_params_online_async.yaml)
7. [Yahboom DOGZILLA README](https://github.com/YahboomTechnology/DOGZILLA)

未创建生产包、未部署、未做真机验证，也未修改现有 README 或人工想法文档。用户评审前不把候选结构写成已确认共识；prototype skill 的结论捕获与独立分支归档留到原型问题得到回答后。
