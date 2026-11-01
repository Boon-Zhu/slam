# B：厂商建图定位复用核查

调研日期：2026-11-01。负责人：Boon-Zhu（3）。这是源码与官方教程调查，不是已选型、已安装或真机验收记录。保持厂商系统与原装硬件，目标 ROS2 Humble，最终节点集中运行于机器人；四模块集成包负责依赖、launch、config 与缺口实现，上游包独立保留。

## 结论

应先检查真机是否有完整可运行的厂商 **Cartographer 建图与纯定位**，再决定是否需要 slam_toolbox/AMCL。官方当前教程确实给出 ROS2 Cartographer 命令，不能把仓库先前列出的 slam_toolbox 候选当成原装实现。已取得的 Pi5 代码附件与教程不一致，并有明确启动缺陷及缺失配置，不能原样作为 B 的可运行交付。公开教程还把部分计算放在电脑虚拟机，不能据此认定机器人已经具备全部计算节点或足够资源。

当前最大阻塞是附件没有教程所指的完整 Cartographer 包与 Lua 配置；需要核实真机已安装工作空间是否另有完整版本。仅从教程 `localization_imu_odom.launch.py` 文件名不能断言它订阅有效 IMU、使用真实里程计，或已配置正确 TF。

已成功取得 [For_RPi5 官方附件目录](https://drive.google.com/drive/folders/1wPXo4vWNy0WeqyFQL01DwRE8YvmT9oJ6) 中 `Pi5docker code.rar`，文件 ID `13sw-2CNvDGtKq7qFpDCTaIhMYWBg5tKJ`，大小 121,664,232 字节，SHA256 `e1d56597897294dc60b3f5bf7fafd2b5f93bca9f51c88de4771d4a3220a148e9`。原包 `/tmp/dogzilla-pi5-confirmed.rar`，可读源码根 `/tmp/dogzilla-pi5-src/Pi5docker code/yahboomcar_ws/src/`。本次没有下载系统镜像。

## 厂商一手证据

官方仓库本次读取的 main 树 SHA 为 `3b62e37f1e25580bc1338cc9f5e2690aec4b966b`；GitHub 主树提供教程 PDF，没有可直接审查的上述 ROS 包源码。独立附件入口是 [Annex_DownloadLink.txt](https://github.com/YahboomTechnology/DOGZILLA/blob/3b62e37f1e25580bc1338cc9f5e2690aec4b966b/Annex_DownloadLink.txt)，指向 Google Drive；下面分别记录教程证据与已取得附件的源码证据。

| 官方材料 | 实际读到的 ROS2 路径 | 能证明／不能证明 |
| --- | --- | --- |
| [Robot dog mapping.pdf](https://github.com/YahboomTechnology/DOGZILLA/blob/3b62e37f1e25580bc1338cc9f5e2690aec4b966b/14.Lidar%20course/Robot%20dog%20mapping.pdf)，步骤 1、3 | Pi5 `./run_humble.sh`；机器人 `ros2 launch bringup Navigation_bringup.launch.py`；建图 `ros2 launch yahboom_bringup Mapping_bring.launch.py` | 证明教程使用 ROS2 和容器入口；教程进入 VM 的 `cartoros2` 后启动建图，不能证明 Pi5 全部节点部署完成 |
| 同教程步骤 5 | `/finish_trajectory`，类型 `cartographer_ros_msgs/srv/FinishTrajectory`；`/write_state`，类型 `cartographer_ros_msgs/srv/WriteState` | 明确 Cartographer 状态保存路径，示例 trajectory ID 为 0；实际应获取当前轨迹 ID，不能硬编码示例值 |
| 同教程步骤 5，Pi5 | 地图状态 `/home/yahboom/yahboomcar_ws/maps/mymap.pbstream`；`ros2 run cartographer_ros cartographer_pbstream_to_ros_map` 转换地图，参数 `map_filestem`、`pbstream_filename`、`resolution` | 可复用状态保存及栅格导出工具；示例分辨率不是项目验收参数。PDF 换行把选项拆开，实施应以本机可执行文件帮助确认拼写 |
| [Robot Dog Navigation.pdf](https://github.com/YahboomTechnology/DOGZILLA/blob/3b62e37f1e25580bc1338cc9f5e2690aec4b966b/14.Lidar%20course/Robot%20Dog%20Navigation.pdf)，Pi5 步骤 3 | `ros2 launch yahboom_dog_cartographer localization_imu_odom.launch.py load_state_filename:=.../mymap.pbstream`，随后 `ros2 launch yahboom_dog_navigation2 navigation2.launch.py use_sim_time:=False map:=.../mymap.yaml` | 区分 Cartographer 重定位和 Nav2 导航；第一版不需要教程后续 Navigation2 Goal 自动驾驶。是否能只启动前者并输出完整定位，需审查 launch/TF |
| 同导航教程，Pi4 | `yahboom_bringup Navigation_bringup.launch.py map_yaml:=... map:=...pbstream` | Pi4 也明确是 `ros2 launch`；不能把 Pi4/Pi5 路径混用，也不能把旧 ROS1 launch 视为 Humble 直接可用 |

PDF 下载及提取仅保存在 `/tmp/dogzilla-mapping/`；未下载系统镜像，未运行任何机器人节点。

## Pi5 附件源码审读：不能直接套用的关键差异

以下路径相对于上面的源码根；在线来源统一为 [Pi5docker code.rar](https://drive.google.com/file/d/13sw-2CNvDGtKq7qFpDCTaIhMYWBg5tKJ/view)，以 SHA256 固定本次所读版本。缺文件结论同时核对 `/tmp/dogzilla-rar-list.txt` 的归档清单，不仅依赖解压目录（初次解压日志报告若干子项错误）。

| 文件／位置 | 实际实现 | 对最短路线的影响 |
| --- | --- | --- |
| `yahboom_bringup/launch/Mapping_bring.launch.py:3,17,29` | 只导入 `Node`，却调用未定义的 `NODE(...)`；include `xgo_bringup/Catographer.launch.py`，此包不在归档；多处 `node_executable` 旧参数 | `NODE` 是执行到该行必然 NameError 的代码缺陷，不是命名风格；缺包也会更早失败。此入口不能原样复用到 Humble |
| `yahboom_bringup/launch/Catographer.launch.py:19` | 依赖 cartographer_ros 包内 `configuration_files/xgo_2d.lua`，启动 Cartographer 与 occupancy grid；也有旧式 Node 参数 | 归档没有任何 `.lua` 文件，也没有 Cartographer 包。算法配置及 TF 分工不能从这份包还原 |
| `yahboom_bringup/launch/Catographer_localization.launch.py:20-56` | 使用 `xgo_2d_loc.lua`；写死 `/home/parallels/cartoros2/src/cartographer_ros/cartographer_ros/configuration_files/mymap2.pbstream`；虽 DeclareLaunchArgument，传给节点的是普通字符串；IMU remap 到 `/imu/data_raw` | 外部覆盖 load_state_filename 不会改变实际节点参数；需修复为 LaunchConfiguration。Lua 缺失，无法验证 pure localization；这不是教程 Pi5 的 `localization_imu_odom.launch.py` |
| `yahboom_bringup/launch/Navigation_bringup.launch.py` | 声明 rf2o，但返回列表注释掉；实际 include xgo_bringup、localization_server，后者又承载 navigation | 不能据此声称已运行激光里程计。归档也没有上述包及教程的 yahboom_dog_cartographer、yahboom_dog_navigation2 |
| `bringup/launch/Navigation_bringup.launch.py` | 启动 MS200、关节状态、URDF、yahboom_base、tf_publisher；独立 wit IMU、App保存入口均被注释掉 | 设备 bringup 的可复用程度明显高于算法 launch；也不能以构造了一个 Node 变量认定其已被启动 |
| `yahboom_dog_joint_state/yahboom_dog_joint_state/yahboomcar_joint_state.py:44` 与定位 launch:56 | 实际 IMU 话题是 `imu/data_raw_self`，上述定位 launch 却期待 `/imu/data_raw` | 当前文件组合存在话题不匹配；需从真机 remap/overlay 核实是否另有适配 |
| `tf_publisher/tf_publisher/tf_publisher.py` | 固定 `base_footprint → base_link` 平移 (0.1154,0,0.047)，每 0.1 秒动态广播 | 这是固定底盘关系，不是 odom；不能填补 `odom → base`。外参的物理正确性仍须 A 核实 |
| `yahboom_base/yahboom_base/base.py` | 订阅 cmd_vel 后调用 DOGZILLALib 运动接口，没有 Odometry 发布 | 不能把这个基础驱动等同于已提供 odom。另有 CHAMP odometry 算法头文件，但设备 bringup 未包含 CHAMP 主启动；库文件存在不证明实际数据链成立 |
| `yahboom_app_save_map/yahboom_app_save_map/yahboom_app_save_map.py` | WebSaveMap 服务，固定 cartoros2 路径，先 INSERT SQLite，再 Popen map_saver_cli；不等待退出、不检查结果，无显式 commit；不保存 pbstream | 不能把响应当作完整保存成功，不满足原地图保留、完整替换和位姿绑定。只借鉴工具调用意图，重做 B 的可靠保存薄层；该脚本依赖的接口包也未见于归档 |

以上均为静态源码结论，未在 Humble 运行，不推定这些附件缺陷就是当前真机的运行状态。真正最短步骤是读取真机 `ros2 pkg prefix` 与实际 launch/Lua：若原装环境另有完整可用版本，优先薄封装；若同样缺失，直接评估现成 Humble 算法包，避免长期修补这份不完整附件。

## Humble 上游核对

以下均核对明确的 `humble` 分支，不借用 Rolling/Jazzy 参数。

| 方案 | 已有可复用能力 | 必须满足的前置／新增工作 |
| --- | --- | --- |
| 厂商 Cartographer | 教程级证据覆盖建图、结束轨迹、写 pbstream、导出栅格、加载 pbstream 定位 | 获取真实包与 Lua；查 `use_odometry`、`use_imu_data`、tracking/published/odom frame、`provide_odom_frame`、pure localization 配置；确认谁发布每段 TF；补项目持久化和定位有效性。当前这些具体值未知 |
| slam_toolbox Humble 建图 | [online_async_launch.py](https://github.com/SteveMacenski/slam_toolbox/blob/humble/launch/online_async_launch.py) 启动 `async_slam_toolbox_node`，支持自己的参数文件 | 需要 LaserScan、扫描时刻有效的 `odom_frame → base_frame` 变换、底盘到雷达外参；它不会替本项目证明 odom 的物理来源与质量 |
| slam_toolbox Humble 定位 | [localization_launch.py](https://github.com/SteveMacenski/slam_toolbox/blob/humble/launch/localization_launch.py) 启动 `localization_slam_toolbox_node`；[定位配置](https://github.com/SteveMacenski/slam_toolbox/blob/humble/config/mapper_params_localization.yaml) 有 map_file_name/map_start_pose 注释入口；支持 initialpose | 加载自己的序列化位姿图，不是 Cartographer pbstream；单独 PGM/YAML 不足以恢复其图定位。需显式核对 mode，样例 YAML 中 mode 仍写 mapping，不能原封不动当最终配置 |
| Nav2 AMCL Humble | [localization_launch.py](https://github.com/ros-navigation/navigation2/blob/humble/nav2_bringup/launch/localization_launch.py) 仅启动 map_server、amcl、localization lifecycle manager；可以独立于路径规划和速度控制运行 | 静态地图、LaserScan、有效 TF；调整实际 base frame 和运动模型，不能套用轮式底盘默认模型后宣称适合四足横移 |

[slam_toolbox Humble README 的接口章节](https://github.com/SteveMacenski/slam_toolbox/blob/humble/README.md#subscribed-topics) 区分 `/slam_toolbox/save_map`（图像地图）与 `/slam_toolbox/serialize_map`（位姿图）；`deserialize_map` 加载后者。其定位文档也明确需要高质量里程计。这意味着“换 slam_toolbox”不能跳过 B 的运动估计核查。

[Humble AMCL 实现](https://github.com/ros-navigation/navigation2/blob/humble/nav2_amcl/src/amcl_node.cpp) 有 `initialpose` 的 `PoseWithCovarianceStamped` 订阅，也支持 `set_initial_pose` 与 `initial_pose.{x,y,z,yaw}`；可用于固定停靠位初始化。初始化可成功接收不等于定位已收敛。其参数内保存位姿的逻辑不是本项目地图标识关联、有效性检查和断电持久化协议，不能依赖参数描述代替磁盘写入验证。

[Humble MapSaver 实现](https://github.com/ros-navigation/navigation2/blob/humble/nav2_map_server/src/map_saver/map_saver.cpp) 提供 `nav2_msgs/srv/SaveMap`，接受地图话题与输出路径并返回结果；它没有替本项目完成“完整新地图替换当前地图，同时作废旧停靠位”的跨文件业务事务。

## 建议最短复用路线（待真机核实后选定）

1. A 交付原装工作空间实际清单、版本、雷达/IMU/反馈及 TF；B 读取厂商 launch/Lua，D 记录当前启动路径。在保留系统条件下先建立厂商算法基线，不重写底层、不先更换算法。
2. B 在统一集成包中封装厂商建图与纯定位两个互斥入口，复用上游工具与参数；D 负责停止运动后切换模式。定位入口去掉自主导航需求，但必须确认移除导航节点后地图和 TF 仍完整。
3. 在机器人上复现建图、保存、加载并记录 CPU/内存/延迟。电脑只保留可视化与遥控；厂商 VM 教程不满足这一部署验收。
4. 如果厂商路线缺源码、依赖不可运行或不能满足定位需要，使用同一录包和物理参考点比较 slam_toolbox 建图 + AMCL；已有 Cartographer 栅格地图也可作为 AMCL 对照输入，前提是 YAML 图像、原点、尺度一致。不要假设 pbstream 可直接交给 slam_toolbox。
5. 若厂商路线可用则优先沿用；若选 AMCL，只启上游定位 launch 的必要节点。任何方案都只允许一个有效的 `map → odom` 发布者。

## B 的真实交付与 A／D 依赖

| B（Boon-Zhu，3）必须做 | 可直接复用 | 依赖 |
| --- | --- | --- |
| 判断原有里程计／运动估计能否使用，形成 TF 发布者表 | 厂商反馈、现有算法 | A 提供实际来源、消息、时间戳、频率、外参；命令积分不能当已测位移 |
| 两种模式及配置、资源验证 | 厂商 Cartographer 或 Humble 上游 launch | D 的统一启动、模式选择；A 的 scan/TF/反馈 |
| 保存成功判定、地图完整性检查、原子提交当前地图、失败保留旧版 | pbstream 写入／栅格转换／MapSaver | D 调用并展示成功或失败；文件写入与地图语义归 B |
| 保存有效位姿、地图 ID 绑定、地图替换后失效、固定停靠位恢复 | initialpose 或厂商已有初始化接口（后者待源码确认） | D 协调停稳、保存、正常关机；操作人员确保断电不搬动 |
| 定位状态与失效判定、拒绝保存无效位姿、人工重置入口 | 算法位姿和诊断输出 | 与 D 定义就绪／失效；C 在定位失效时继续独立的雷达保护 |
| 回放与真实参考点重复验收、最后提供导出 | rosbag、已有地图工具 | A 首份录包；D 测试记录与共享真机安排 |

建议持久化形式是先在临时位置完整生成地图文件与 manifest，再提交当前地图引用；manifest 包含地图标识、算法和格式、文件清单／校验值、坐标系，位姿绑定同一地图标识。具体实现待接口设计；这不是要求新增多地图产品功能，也不是此次已实现的代码。

## 真机必须核实的最小清单

- `ros2 pkg prefix` 和实际 package.xml：bringup、yahboom_bringup、yahboom_dog_cartographer、yahboom_dog_navigation2、cartographer_ros 是否存在；其源码、版本、许可及依赖能否提取。教程包名大小写保持原样。
- 两个 localization/mapping launch 实际 include 链；Lua 是否为纯定位；是否加载 frozen 轨迹；是否产生新的可变地图，能否明确禁止修改持久地图。
- scan、IMU、odom 真实话题与类型；`/odom` 从何而来，是否只是收到 cmd_vel 后积分；时间戳、容器时间、use_sim_time、TF 可查询性。
- 逐边确认 map/odom/base/laser/imu frame；避免启动新定位器后与原装 Cartographer 或其他节点重复发布 TF。
- 机身俯仰/横滚/起伏时扫描是否仍可用，原装步态与速度对定位和运算负载的影响。
- 初始位姿如何传给厂商 Cartographer，固定停靠位是否能稳定恢复；教程未展示这段完整流程，不宣称已有自动重启恢复功能。
- 地图所在容器目录是否挂载到持久存储；写盘失败、容器重启和地图替换后旧位姿失效是否按要求工作。
- 所有 B 节点集中树莓派时的资源与连续运行表现；约 50 厘米目标需物理参考点实测，地图外观不能代替定位误差。

## 本次范围与限制

完成官方 PDF 文本读取、Pi5 代码附件归档清单及相关源码审读、Humble 上游接口核对；未进行算法选型、项目安装、配置修改、节点启动、录包或真机测量。临时 PDF/解压工具只用于 `/tmp` 研究。AGENTS.md 引用的 `docs/Standard/coding-standard.md` 在当前工作树不存在；本次仅增加研究 Markdown，没有编写项目代码或配置。
