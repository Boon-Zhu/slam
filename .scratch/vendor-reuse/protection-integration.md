# C 运动保护与 D 运行集成：上游复用核查

日期：2026-11-01。范围：原装 DOGZILLA S2/MS200、受保护人工遥控、机器人运行节点、电脑 SSH；ROS2 Humble 为目标，未核实实机版本。本记录是源码研究，没有安装、编译、仿真或真机验证。

## 结论

`nav2_collision_monitor` 可独立于规划器、控制器和自主导航使用，但本次检查的 Humble 实现不是完整的故障停车与恢复门控组件。C 不能仅交付一份 Nav2 参数：至少还需遥控会话/新鲜度门控、雷达与 TF 有效性监督、独立定时停车、恢复后新指令规则及结构化状态；A 需兜底验证保护进程消失时的实际停止。D 可复用 launch/lifecycle 管理机制，但需要自己的业务就绪、互斥模式切换与故障分组。

重要版本界限：以下所有 Nav2 结论固定于官方 `humble` 分支当次解析的 commit **`3c3db59d6969d8ecee8e68468693d006397f4a0c`**，包内版本 **1.1.20**。不推断所有历史 Humble 二进制、后续 backport 或厂商改版都相同。实施前核对实机 Debian 包版本/源码 SHA。公开文档中的新功能不能自动视为该实现已有。[package.xml](https://github.com/ros-navigation/navigation2/blob/3c3db59d6969d8ecee8e68468693d006397f4a0c/nav2_collision_monitor/package.xml#L4-L10)

## 已确认接口和运行依赖

- 输入/输出均为 `geometry_msgs/msg/Twist`，默认 `cmd_vel_raw → cmd_vel`，使用 x/y/angular.z；不是 `TwistStamped`。可重映射到项目 C→A 通路。独立 launch 只启动 collision monitor 与 lifecycle manager，不需要 planner/controller/BT navigator。[订阅发布](https://github.com/ros-navigation/navigation2/blob/3c3db59d6969d8ecee8e68468693d006397f4a0c/nav2_collision_monitor/src/collision_monitor_node.cpp#L64-L68)、[独立 launch](https://github.com/ros-navigation/navigation2/blob/3c3db59d6969d8ecee8e68468693d006397f4a0c/nav2_collision_monitor/launch/collision_monitor_node.launch.py)
- `scan` 是 `sensor_msgs/msg/LaserScan`，SensorDataQoS；支持 scan/pointcloud/range 源。关键参数是 `cmd_vel_in_topic`、`cmd_vel_out_topic`、`base_frame_id`、`odom_frame_id`、`transform_tolerance`、`source_timeout`、`base_shift_correction`、`stop_pub_timeout`、`polygons`、`observation_sources`。[节点参数/源工厂](https://github.com/ros-navigation/navigation2/blob/3c3db59d6969d8ecee8e68468693d006397f4a0c/nav2_collision_monitor/src/collision_monitor_node.cpp#L183-L340)、[scan订阅](https://github.com/ros-navigation/navigation2/blob/3c3db59d6969d8ecee8e68468693d006397f4a0c/nav2_collision_monitor/src/scan.cpp#L45-L63)
- `base_shift_correction=true` 会经固定参考坐标系（默认 odom）修正源时刻至当前时刻；false 仅要求传感器到 base 的 TF，牺牲时移修正而解除对状态估计坐标系依赖。两者都不需要 map→odom 或 AMCL；可满足“全局定位失效仍人工遥控”，但必须区分全局定位失效与本地 TF/odom 失效。[变换分支](https://github.com/ros-navigation/navigation2/blob/3c3db59d6969d8ecee8e68468693d006397f4a0c/nav2_collision_monitor/src/scan.cpp#L78-L101)
- 可用形状仅 polygon/circle，可用动作 stop/slowdown/approach。该 SHA 不提供新版本 velocity polygon 或 limit 动作；`max_points` 不能照抄新版 `min_points`。示例数值和 `use_sim_time=True` 均不是实机建议。[形状](https://github.com/ros-navigation/navigation2/blob/3c3db59d6969d8ecee8e68468693d006397f4a0c/nav2_collision_monitor/src/collision_monitor_node.cpp#L238-L280)、[动作参数](https://github.com/ros-navigation/navigation2/blob/3c3db59d6969d8ecee8e68468693d006397f4a0c/nav2_collision_monitor/src/polygon.cpp#L239-L280)、[示例配置](https://github.com/ros-navigation/navigation2/blob/3c3db59d6969d8ecee8e68468693d006397f4a0c/nav2_collision_monitor/params/collision_monitor_params.yaml)

## 按项目约束审计

| 项目要求 | 本次源码证据与结论 | 项目需补内容 |
| --- | --- | --- |
| 限制危险方向并允许安全退开 | STOP 只看区域点数，触发即把 x/y/转速全清零；前方 STOP 区被占据时后退也会被阻止。SLOWDOWN 对完整速度等比例缩放。 | 方向规则/安全退开不能仅由静态 STOP 区声称实现。评估 APPROACH 或有界自有方向过滤；真机验证。 |
| 雷达中断停车 | `Scan::getData` 在无数据、过期或 TF 失败时直接返回，不生成故障停车信号；`process` 继续用收集到的点判断，默认动作保留输入速度。单 scan 源失效、普通正阈值配置下，空点集会允许输入速度通过。 | C 独立监视首帧、数据时间/接收时间、TF 和有效覆盖；失败明确发零。不能把 source_timeout 当停车 watchdog。 |
| 遥控中断停车 | 处理只由 `cmdVelInCallback` 调用；所审节点实现没有命令超时检查定时器。无新输入就不执行新保护运算。 | 独立周期看门狗；A 的命令失联兜底；不依赖“恰好又来一帧指令”。 |
| 恢复必须新指令 | 节点没有遥控会话、序号、失效后重新武装状态。Twist 也无消息时间戳。 | 断连/雷达故障时作废旧命令，恢复后只接受新的有效人工输入。重复旧值的自动重发不能算新的人工意图。 |
| 转身扫掠空间 | APPROACH 按 x/y/angular.z 投影运动并变换障碍点，包含旋转几何；不是只检查正前方。 | 轮廓必须覆盖步态时肢体扫掠，配置时间步长与保守裕量；不能从二维几何推断真实停止距离。 |
| 有足够空间才退开 | 无有效回波不等于已证实该方向有空隙；当前实现只处理范围内点，不建立已知/未知可通行空间语义。 | 确认原装视野、遮挡和每个允许运动方向的观测覆盖；缺失方向禁止放行。 |
| 定位失效继续遥控 | 算法不使用全局定位，可分离运行。 | C 的运行组不能因 AMCL 故障被共同 lifecycle teardown；D 单独提示定位不可用。 |
| 限制与故障原因输出 | `printAction` 输出日志；此节点中没有项目所需的结构化保护状态发布接口。 | C 状态话题/服务及 D 的提示映射；不能以日志代替稳定业务接口。 |

直接证据：

1. **雷达失效路径**：[Scan::getData L65–101](https://github.com/ros-navigation/navigation2/blob/3c3db59d6969d8ecee8e68468693d006397f4a0c/nav2_collision_monitor/src/scan.cpp#L65-L101)、[Source::sourceValid](https://github.com/ros-navigation/navigation2/blob/3c3db59d6969d8ecee8e68468693d006397f4a0c/nav2_collision_monitor/src/source.cpp#L76-L94)、[process L343–402](https://github.com/ros-navigation/navigation2/blob/3c3db59d6969d8ecee8e68468693d006397f4a0c/nav2_collision_monitor/src/collision_monitor_node.cpp#L343-L402)。`getData` 为 void，准确说法是调用者没有拿到故障返回值，而非忽略一个 bool 返回值。上述空点集放行是静态控制流推导，尚未执行故障注入测试。
2. **命令触发与停止输出**：[cmdVelInCallback / publishVelocity L149–180](https://github.com/ros-navigation/navigation2/blob/3c3db59d6969d8ecee8e68468693d006397f4a0c/nav2_collision_monitor/src/collision_monitor_node.cpp#L149-L180)。`stop_pub_timeout` 是已进入零速度后停止重复发布零的时限，完全不是“多久没指令就停车”。TF buffer 的 timer interface 也不是遥控看门狗。
3. **方向与轮廓**：[STOP/SLOWDOWN/APPROACH](https://github.com/ros-navigation/navigation2/blob/3c3db59d6969d8ecee8e68468693d006397f4a0c/nav2_collision_monitor/src/collision_monitor_node.cpp#L405-L457)、[碰撞时间模拟](https://github.com/ros-navigation/navigation2/blob/3c3db59d6969d8ecee8e68468693d006397f4a0c/nav2_collision_monitor/src/polygon.cpp#L175-L207)、[运动学](https://github.com/ros-navigation/navigation2/blob/3c3db59d6969d8ecee8e68468693d006397f4a0c/nav2_collision_monitor/src/kinematics.cpp#L24-L72)。APPROACH 初始轮廓中已有足够障碍点时也会返回碰撞时间零，不能保证从重叠障碍中退开。
4. **APPROACH 的隐藏接线需求**：polygon/approach 分支必须读取 `footprint_topic`，不会用 YAML `points`；默认 `local_costmap/published_footprint`。可提供独立有效轮廓发布者而不启动 costmap，但要核对消息/QoS和首帧就绪；不能直接照抄此默认话题后认为已工作。[参数分支 L314–324](https://github.com/ros-navigation/navigation2/blob/3c3db59d6969d8ecee8e68468693d006397f4a0c/nav2_collision_monitor/src/polygon.cpp#L314-L324)、[轮廓更新 L142–160](https://github.com/ros-navigation/navigation2/blob/3c3db59d6969d8ecee8e68468693d006397f4a0c/nav2_collision_monitor/src/polygon.cpp#L142-L160)
5. **关停不等于发零**：deactivate 禁用处理和 publisher，shutdown 仅记录日志；不能以生命周期切换替代显式停车握手。[L99–146](https://github.com/ros-navigation/navigation2/blob/3c3db59d6969d8ecee8e68468693d006397f4a0c/nav2_collision_monitor/src/collision_monitor_node.cpp#L99-L146)

## D 可以直接复用什么

独立 launch、参数文件路径/namespace/use_sim_time 重写，以及 lifecycle manager 的 configure→activate 顺序可复用。manager 的 startup 成功以节点状态转换为依据，并启动 bond 定时检查；不核实有效 scan、轮廓首帧、地图版本绑定或真实停止接口。某节点 bond 失效会 reset 同组节点，因此建议 C/A 保护运行组与 B 建图定位组分离，避免全局定位故障切断受保护人工遥控。[startup](https://github.com/ros-navigation/navigation2/blob/3c3db59d6969d8ecee8e68468693d006397f4a0c/nav2_lifecycle_manager/src/lifecycle_manager.cpp#L279-L294)、[bond 故障](https://github.com/ros-navigation/navigation2/blob/3c3db59d6969d8ecee8e68468693d006397f4a0c/nav2_lifecycle_manager/src/lifecycle_manager.cpp#L412-L447)

D 仍需组合业务流程：启动先禁止运动→检查 A/C 就绪→允许新遥控；切换前停稳/门控→停旧 B 模式→启动新 B 模式→发布状态；保存/重启调用 B 的事务式地图与位姿接口。launch 成功、lifecycle active、bond 连通均不能替代这些完成条件。这些是基于项目 README 的集成设计建议，尚未实现。

## 最小组合与分工建议（待采纳）

`人工遥控来源 → C 会话/新鲜度/恢复门控 → 障碍过滤候选 → C 最终有效性门控与周期停车 → A 运动适配/失联兜底 → 原装步态`

- C 主要集成包保存输入适配、配置、门控、状态与测试。障碍过滤候选可以是固定版本 collision_monitor；方向退开、无观测空间、轮廓缺失行为必须先小实验验证。若补齐所需行为最终需要大量旁路/动态启停 polygons，改为小范围自有方向过滤器可能更清晰，但此时不是“已有 Nav2 包直接满足”。
- A 交付可验证的停止语义和最后一道失联停止；C 进程死亡时不能要求同一 C 进程继续运行看门狗。使用哪层已有 watchdog 需实机证据。
- D 主要集成包维护顶层 launch、模式入口和就绪/故障编排，上游包作为独立依赖。无需复制完整 Nav2 navigation launch，也无需因包依赖 `nav2_costmap_2d` 就启动 costmap 节点。
- 首个离线门槛：持续非零遥控下断 scan/断 TF、无新遥控、故障恢复时仅旧重发、前障碍后退、原地转身、无 footprint、AMCL 故障但本地感知正常。最后两层真实停车/步态惯性必须真机验证；本次没有测试结果。

## 厂商资料与 Pi5 源码补充

已枚举官方 DOGZILLA 仓库固定 commit `3b62e37f1e25580bc1338cc9f5e2690aec4b966b` 的树，相关项目是 PDF 教程，而非可审查的 ROS2 package 源码；不能从教程标题断言已有遥控保护过滤器。

两个官方 PDF 已下载至 `/tmp/slam-protection-audit/` 并由并行研究代理使用 pypdf 提取，文本分别为 `avoid.txt`、`keyboard.txt`：

- 避障教程明确描述启动后自动前进、遇障调整姿态避开再继续前进，因此它是自主避障演示，不能直接等同于“人工指令经过限制过滤”。教程给出 `yahboom_laser/laser_Avoidance_xgo_RS200.py`，同时标注 MS200；文件名中的 RS200 不足以推断实际雷达型号。Pi4 示例用 `YahboomStart.service`、`cartographer_ws2`；Pi5 示例进入 `run_humble.sh` 容器后执行 `ros2 launch bringup Navigation_bringup.launch.py` 和 `ros2 run yahboom_laser laser_Avoidance_xgo_RS200`。这些原为源码定位线索；随后取得 Pi5 源码，以下补充以源码为准。其核心代码说明又明确拿 X3/A1 举例，不能用片段证明原装 S2 全部方向/故障行为。[避障教程](https://github.com/YahboomTechnology/DOGZILLA/blob/3b62e37f1e25580bc1338cc9f5e2690aec4b966b/14.Lidar%20course/2.%20Obstacle%20avoidance.pdf)
- 键盘教程提供 SSH 到机器人、启动 `YahboomStart.service`、在 `cartographer_ws2` 中运行 `teleop_twist_keyboard` 的操作路径。这支持“电脑仅 SSH、节点在机器人运行”的用法，但该教程没有证明 SSH 断线自动停车、指令经过 C 或恢复不重放，不能据此放行演示。此旧教程路径也不能当作 Pi5/S2 实机目录事实。[键盘控制教程](https://github.com/YahboomTechnology/DOGZILLA/blob/3b62e37f1e25580bc1338cc9f5e2690aec4b966b/12.ROS%20robot%20dog%20basic%20control%20course/4.%20Keyboard%20control.pdf)

主代理另已取得小型 `DOGZILLALib` 并指出 `turn(step)` 会将小幅非零参数提升到最小幅值；此处不将 `step` 当作已核实的 rad/s。C↔A 必须校准 Twist 的物理单位、限幅/量化与最小动作幅度，不能把 collision_monitor 比例缩小输出解释成实机同比减速。完整代码来源/指纹与停止接口证据由设备研究报告记录；本代理尚未验证硬件响应。

所有 Nav2 下载源码存于 `/tmp/slam-protection-audit/nav2_*`，可复查；未下载系统镜像或厂商大型资源包。


### 后续取得的 Pi5 源码：更新上述 PDF 边界

本轮后来取得官方资源中的 `Pi5docker code.rar`，已解压至 `/tmp/dogzilla-pi5-src/Pi5docker code/yahboomcar_ws/src`（下称 `src/`）；归档 SHA256 为 `e1d56597897294dc60b3f5bf7fafd2b5f93bca9f51c88de4771d4a3220a148e9`。资源来源链与下载记录见设备研究报告。以下引用归档内实际源码，不代表实机安装版本；目录同时带 build/install 产物，本次读原始 package 路径。

**厂商避障不能直接复用为 C。** [laser_Avoidance_xgo_RS200.py](</tmp/dogzilla-pi5-src/Pi5docker code/yahboomcar_ws/src/yahboom_laser/yahboom_laser/laser_Avoidance_xgo_RS200.py:17>) L17–21 只订阅 `/scan`、`/JoyState`，直接发布 `/cmd_vel`，没有人工 Twist 输入。L30–39 默认 `Switch=False`，因此实际需开启才开始自动运动，PDF 的“启动即前进”描述不够精确。L73–77 在 Joy_active 或 Switch 关闭时，只在 Moving=true 时发一次零然后返回，这是让出控制，不能保护手柄路径。L81–144 自己生成前进/转弯，多个分支仍保留正向 linear.x；L86 等在回调中 sleep，未做机身扫掠或已知可退空间判断。

**timer 并不监控故障。** 同文件 L41–49 的 0.01s timer 只读取参数；全部速度生成在 scan 回调 L55–144 内，未检查 scan 时间戳，也没有遥控 heartbeat/命令 lease。scan 停止时，该节点没有独立发零的路径。仅此源码足以否定“厂商避障已经完整处理雷达断流停车”；硬件是否另有 watchdog 仍需 A 验证。

**直达运动接口和旁路已存在。** [base.py](</tmp/dogzilla-pi5-src/Pi5docker code/yahboomcar_ws/src/yahboom_base/yahboom_base/base.py:9>) L9 订阅相对 `cmd_vel`，L24–26 在所有分量低于阈值时调用 stop，L40–42 将分量乘40交给 move/turn；该文件没有周期看门狗。默认根 namespace 下，避障直接 `/cmd_vel → base → DOGZILLALib`，未插入 C。还存在 `publisher_member_function.py` 直接发 cmd_vel，以及 `control_test.py` 直接调用 DOGZILLALib.move；原始应用/其他行为节点是否正在运行必须实机排查，不能仅改一个 topic 就保证单一执行权。演示时应只保留 C 的受保护输出为 base 输入，停止无关自主行为和串口直控进程；厂商手柄/APP 的具体部署路径由 A 核实。

**同名 launch 的职责不同。** [bringup/Navigation_bringup.launch.py](</tmp/dogzilla-pi5-src/Pi5docker code/yahboomcar_ws/src/bringup/launch/Navigation_bringup.launch.py:76>) 实际加入 LaunchDescription 的只有 MS200 driver、dog_joint_state、URDF、yahboom_base 和 tf_publisher；IMU、app_map_save、RViz 虽被创建但未加入运行列表。不能从 Navigation 名称推断它启动完整导航，也不能把声明过 IMU 对象当作实际启用 IMU。另一个 [yahboom_bringup/Navigation_bringup.launch.py](</tmp/dogzilla-pi5-src/Pi5docker code/yahboomcar_ws/src/yahboom_bringup/launch/Navigation_bringup.launch.py:1>) 则选择定位与 navigation_server，并引用 `xgo_bringup`；应由 B 核对具体组件/过时命名，不能与前者混用。`bringup/bringup.launch.py` 还有不完整 `from launch.actions` 行，未运行，只能判断其不能直接当成熟集成入口。

**D 的复用边界更明确。** 可摘取实际驱动/模型/base 的 include 组合，整理为本项目有明确名称的设备启动层；需要补参数化路径、C 插入点、唯一运动发布权、首帧/TF/停止就绪检查。现有 launch 没有模式互斥、停稳确认或项目地图事务。`YahboomStart.service` 与 `run_humble.sh` 在本次已解出的 workspace 源码范围内尚未核得定义，PDF 只证明它们的使用命令，不能推断开机具体启动哪些 APP/串口程序。实机 systemd/docker/process 列表仍是检查旁路的必要证据。
