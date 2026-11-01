# DOGZILLA 设备与运动代码复用调查

调查日期：2026-11-01。范围：官方公开资料与源码静态审查；未运行厂商程序、未编译、未连接真机。目标为原装 MS200、机器人端运行节点、Ubuntu 22.04 / ROS2 Humble；这不代表实机已具备该环境。

## 1. 已实际取得的源码与可复现入口

GitHub 当前快照 `3b62e37f1e25580bc1338cc9f5e2690aec4b966b` 的递归树主要是教程 PDF/图片，不是 ROS workspace。不能因 README 标注 Humble 就认为驱动源码已公开在 GitHub；实际入口为官方 [Annex_DownloadLink.txt](https://github.com/YahboomTechnology/DOGZILLA/blob/3b62e37f1e25580bc1338cc9f5e2690aec4b966b/Annex_DownloadLink.txt)。它指向 [官方附件根目录](https://drive.google.com/drive/folders/13RYtBkce3EF5qFy8eSqtLbtFiruhWlqm)，内有 [2.Code](https://drive.google.com/drive/folders/1w_KtXikT2YsU6ldEhc1OWFUHuNsjOpVj)，再分 [For_RPi4](https://drive.google.com/drive/folders/1D3WbJbo73qDKZGiu0uaFZJiA80A96Bkd) 与 [For_RPi5](https://drive.google.com/drive/folders/1wPXo4vWNy0WeqyFQL01DwRE8YvmT9oJ6)。本次已下载、成功解压并读到下列真实内容，不只是看目录。

| 产物 | 官方链接与文件名 | 大小 / SHA256 | 本地证据 |
| --- | --- | --- | --- |
| Pi5 workspace | [Pi5docker code.rar](https://drive.google.com/file/d/13sw-2CNvDGtKq7qFpDCTaIhMYWBg5tKJ/view) | 121664232 bytes；`e1d56597897294dc60b3f5bf7fafd2b5f93bca9f51c88de4771d4a3220a148e9` | `/tmp/dogzilla-pi5-confirmed.rar`，已解压 `yahboomcar_ws/src` |
| 通用旧 Python 串口库 | [DOGZILLALib.zip](https://drive.google.com/file/d/1rHRu819gUmnO0LGCuovczyJ4_VC917O4/view) | 5610 bytes；`a68db7c7bba1183cf06ad8fab2c8109f04103193d6ce4aebb8b2d6267b1ff138` | `/tmp/dogzilla-lib`，版本 2.0.7 |
| 通用旧 APP/手柄代码 | [app_dogzilla.zip](https://drive.google.com/file/d/1mPh2RPnhy6-YM_IzrWXrizDpI3Hz2nJC/view) | 19330 bytes；`a43929e949fa0e64ee9fa6bda3c47cfab5251e3aaee875e8ef10943be99bc024` | `/tmp/dogzilla-app` |

Pi5 源码根目录（下文 `SRC/`）为 `/tmp/dogzilla-pi5-src/Pi5docker code/yahboomcar_ws/src/`。所有 `SRC/文件:行` 均指上述官方 RAR 中 `Pi5docker code/yahboomcar_ws/src/文件`，官方未提供逐文件网页，需按文件 ID + 包哈希 + 内部路径复核。RAR 列表在 `/tmp/dogzilla-rar-list.txt`。附件会被更新，不能把下载时间当软件版本；ROS 包多为 `0.0.0`。源码中混有 `src/build`、`src/install`、core 文件及旧 ROS1 launch，不能整体复制成干净项目。未下载系统镜像，未下载另一个 494 MB VM code.rar。

下载说明：web 无法解析 Drive，但 curl 可读公开 HTML。大包首次 `/uc` 返回 Google 病毒扫描确认 HTML，按其返回的下载表单（含 uuid）才取得真实 RAR。使用 Ubuntu 官方 unrar 软件包解出本地工具到 `/tmp`，没有系统安装，也没有执行厂商代码。

## 2. Pi5 真实启动链

官方 [建图教程 PDF](https://github.com/YahboomTechnology/DOGZILLA/blob/3b62e37f1e25580bc1338cc9f5e2690aec4b966b/14.Lidar%20course/Robot%20dog%20mapping.pdf) 区分 Pi4 与 Pi5，Pi5 先关闭原“大程序”、`./run_humble.sh` 进入 Docker，再执行 `ros2 launch bringup Navigation_bringup.launch.py`。教程还把建图节点放在外部虚拟机；本项目要求机器人端运行，不能直接沿用其部署拓扑。

实际 `SRC/bringup/launch/Navigation_bringup.launch.py:9-99`：

- 启动 `oradar_lidar/launch/ms200_scan.launch.py`。
- 启动 `yahboom_dog_joint_state`，产生关节状态和 IMU。
- 启动 `yahboom_description/yahboom_urdf.launch.py` 的 robot_state_publisher。
- 启动 `yahboom_base/yahboom_base.launch.py` 的 `base` 可执行入口。
- 启动 `tf_publisher`。
- `wit_ros2_imu` 虽有节点定义（`/dev/imu_usb`、9600、重映射 `/wit/imu → /imu/data`），但返回列表注释掉该节点，**没有随这份 launch 启动**。不能据此要求新增外接 IMU。
- RViz 与 app_map_save_node 同样注释，不属于实际启动集合。

依据：上述 [Pi5 官方包](https://drive.google.com/file/d/13sw-2CNvDGtKq7qFpDCTaIhMYWBg5tKJ/view) 内 launch；`yahboom_base/launch/yahboom_base.launch.py:9-25`；`yahboom_dog_joint_state/launch/yahboom_dog_joint_state.launch.py:16-24`。

## 3. MS200 驱动可复用证据

`SRC/oradar_lidar/launch/ms200_scan.launch.py:25-66` 实际使用 `oradar_lidar` 包、`oradar_scan` executable、节点名 `MS200`，参数如下（仅厂商默认，非本项目已验证值）：

| 项 | 代码值 |
| --- | --- |
| 型号 / 串口 / 波特率 | `MS200` / `/dev/ttyAMA1` / `230400` |
| 输出 | `/scan`，`sensor_msgs/msg/LaserScan`，`frame_id=laser_frame` |
| 扫描 / 距离默认 | 0–360 度、0.05–20.0、`clockwise=False`、`motor_speed=10` |
| 静态 TF | `base_link → laser_frame`，平移 `(0,0,0.18)`，零旋转 |

真实 C++ 在 `SRC/oradar_lidar/src/oradar_scan_node.cpp`，不是空壳：254 行创建 LaserScan publisher（depth 10）；323–344 行先取 ROS `now()`，再 `GrabFullScanBlocking(...,1000)`，用前后主机时刻差生成 `scan_time`，成功才发布；109–122 行填 header 和 `time_increment`。这证明时间戳来自主机采集调用前，尚不能证明与真实第一束光同步。读取超时后不发布并继续循环，**驱动没有运动停车接口**。C 的雷达失效停车需独立消费新鲜度并下发零。

本包 CMake 同时含 ROS1/ROS2 分支，当前 `package.xml` 是 `ament_cmake` + `rclcpp` + `sensor_msgs`；`.launch` 文件存在不等于这是 ROS1 包。`package.xml` 声明 MIT，`LICENSE` 有 ORADAR MIT 正文。这一具体驱动可作为优先复用对象，仍需干净 Humble 构建、串口权限/映射、频率/QoS、遮挡/外参及断流验证。依据：[Pi5 官方包](https://drive.google.com/file/d/13sw-2CNvDGtKq7qFpDCTaIhMYWBg5tKJ/view)，内部上述路径及 `oradar_lidar/CMakeLists.txt:13-53`、`package.xml`、`LICENSE`。

## 4. 运动接口已找到，但不能原样作为安全执行器

`SRC/yahboom_base/yahboom_base/base.py:6-45` 创建 `cmd_vel_sub`，订阅相对名 `cmd_vel`、`geometry_msgs/msg/Twist`、队列深度 1。每次回调提取 x/y/z；三项绝对值都小于 0.05 才调用 `DOGZILLA.stop()`；否则各限幅 ±100，再将三个轴乘 40 送给 `move('x', ...)`、`move('y', ...)`、`turn(...)`。代码不证明这些输入是经过标定的 m/s、rad/s 映射。无定时看门狗、最后指令时间、雷达输入、连接状态、恢复锁存；`rclpy.spin` 后的清理也没有显式停车。失去上游消息不会由这个节点主动发零。依据：[Pi5 官方包](https://drive.google.com/file/d/13sw-2CNvDGtKq7qFpDCTaIhMYWBg5tKJ/view)，`base.py:1-61`。

独立 [DOGZILLALib 2.0.7](https://drive.google.com/file/d/1rHRu819gUmnO0LGCuovczyJ4_VC917O4/view) 静态审查结论：

- `DOGZILLALib/DOGZILLALib.py:121-122` 默认 `/dev/ttyAMA0`、115200、serial read timeout 0.5；这是串口读取超时，**不是运动失联超时**。
- 155–159 行 `stop()` 依次 `move_x(0)`、`move_y(0)`、`mark_time(0)`、`turn(0)`；仅串口写入，没有停稳确认。
- 169–195 行 x/y 限幅 ±20/±18，yaw ±70，并将绝对值小于 30 的非零转向提升到 ±30。因此低速小角速度未必能线性执行；这些 step 的物理单位和实机库行为需比对，不应直接把这些数字作为保护参数。
- 477–547 行可读取舵机角、电池、固件版本、roll/pitch/yaw；单次读取失败可能返回空数组或零，没有统一有效性标志。
- 此版本 **没有 `read_imu_raw()`**，但 Pi5 joint_state 源码实际调用该方法；RAR 完整文件列表也没有 DOGZILLALib 源码。这是实质依赖缺口，不能把旧库装进 Humble 就宣称可运行。

A 最小适配需明确串口唯一所有者、命令单位与非线性映射、有效输入检查、保护后命令专用入口和停车接口；C 负责控制消息期限与雷达期限，A 可增加执行侧看门狗作为额外闭环。必须真机验证零指令、急停语义、实际停止距离和进程异常停止行为。该段是设计建议，未实施。

## 5. 原装 IMU / 关节反馈：有代码，质量与版本存在具体缺口

`SRC/yahboom_dog_joint_state/yahboom_dog_joint_state/yahboomcar_joint_state.py` 是真实 ROS2 节点：39 行实例化 DOGZILLA；43–44 行输出 `/joint_states`（JointState）及 `imu/data_raw_self`（Imu），IMU frame 为 `imu_link`。64–69 行读 12 个关节角并变换符号/转弧度；98–121 行从 `read_imu_raw()` 取三轴加速度、角速度及 RPY，转换 quaternion。它不是外接 WIT 节点，也没有发布 Odometry。依据：[Pi5 官方包](https://drive.google.com/file/d/13sw-2CNvDGtKq7qFpDCTaIhMYWBg5tKJ/view)，以上内部文件。

发现以下必须修复或核实的实现问题：

1. timer 为 0.05 秒，但回调明确 `time.sleep(0.1)`，另有串口读取成本；不能宣称发布频率为 20 Hz。关节 velocity 仍除固定 0.05，非实际 dt（46–47、77–88、96 行）。
2. `imu_raw[0] != 0` 才更新 `last_imu`；当第一个加速度分量为零时复用旧 IMU，却在 111 行打当前 stamp。合法零值与读取失败没有分开，消费者单查消息年龄会被误导（98–111 行）。首次数组为空时只捕获 IndexError。
3. RPY 直接进 sin/cos，是否弧度依赖未取得的新库；加速度/角速度未显式单位换算，covariance 未赋值。不能认定满足 ROS IMU 单位和有效性契约。
4. 关节名第二项是 `lf_lower_leg_link`，需对照 URDF joint 名修正；velocity 的符号也需与 position 统一核对（59–88 行）。
5. base 节点和 joint_state 节点分别实例化 DOGZILLA，可能同时访问同一串口；协议是否允许多进程读写、flushInput 是否丢回应需核实，不能假定安全。

`/odom` 不是本驱动反馈。源码包含 CHAMP odometry 类及 `champ_bringup`，但 Navigation_bringup 没有启动 CHAMP。查到“里程计代码存在”不等于这条设备启动链产生 odom；其来源与真实建图路径需结合 [mapping.md](mapping.md) 再核查，真机录包前不得把控制积分当实测位移。

## 6. 已证实 TF 冲突与旧遥控旁路

**默认总 launch 存在同一 TF 边不同数值双发布。** `Navigation_bringup` 同时启动 description 和 tf_publisher；description 默认加载 `yahboom_xgo_rviz.xacro`，其中第 7–12 行固定 `base_footprint → base_link` 为 `(0,0,0.010)`；`SRC/tf_publisher/tf_publisher/tf_publisher.py:16-30` 又每 0.1 秒广播同一边 `(0.1154,0,0.047)`。两者不一致，必须选择唯一来源再验证原装外参。描述文件还存在 `/home/yahboom/cartoros2/...` 绝对 mesh 路径，部署路径需清理。依据：[Pi5 官方包](https://drive.google.com/file/d/13sw-2CNvDGtKq7qFpDCTaIhMYWBg5tKJ/view)，上述路径及 `yahboom_description/launch/yahboom_urdf.launch.py:18,57-69`。

另已取得的 [通用 APP 代码](https://drive.google.com/file/d/1mPh2RPnhy6-YM_IzrWXrizDpI3Hz2nJC/view) 属独立 `/home/pi` 时代路径，不能视为当前 Pi5 上正在运行的软件，但它确实展示另一条必须排查的串口入口：

- `app_dogzilla.py:13,30,345-346` 直接 DOGZILLALib 控制，未经过 ROS cmd_vel。
- `app_dogzilla.py:547,566,591-593` 阻塞 socket，无命令期限；断开路径只 close socket、切 Home，无显式 stop。不能从“TCP断开”推出会停步。
- `joystick_dogzilla.py:334-376` 断连后返回状态、等待、重连，无显式 stop；服务 `my_service/yahboom_joystick.service` 默认 User=pi，直接执行 `/home/pi/DOGZILLA/app_dogzilla/joystick_dogzilla.py`。

实机需检查 APP、手柄、语音、开机服务、docker 外控制程序是否仍有直接写串口通路；所有运动入口都应进入 C。以上并不证明实机已存在这些进程。

## 7. 复用判断与人员细化前必须解决的事实

| 类别 | 结论 |
| --- | --- |
| 可直接作为上游组件候选 | MS200 `oradar_lidar` + SDK，有真实 ROS2 分支、MIT 文件；不是从零编写雷达驱动。先干净构建及实机验收 |
| 配置适配 | 串口设备/权限、最小 robot-only launch、MS200 scan/QoS、TF 唯一发布者和原装外参、描述文件路径、Humble 依赖版本 |
| 需要补代码/修现有实现 | base 执行适配与看门狗/退出停车；IMU有效性、时间戳、实际dt和单位；串口并发所有权；C 的双超时、恢复需新指令、方向保护；统一遥控输入 |
| 必须上机核实 | OS/ROS/docker、实际 DOGZILLALib版本与源码路径、`read_imu_raw`实现与固件、串口、默认服务、真实 scan/imu/TF、运动响应/停距、真实 odom来源、树莓派资源 |
| 许可仍未明确 | `yahboom_base` 与 `yahboom_dog_joint_state` 的 package.xml 为 `TODO: License declaration`；独立库和APP ZIP无LICENSE。不能把 oradar MIT 推广到全部厂商代码。取得/阅读源码不代表已确认可重新分发 |

调查已从“厂商可能提供代码”推进到具体文件级证据，但仍不能给出整包即用承诺。A 可以围绕已有驱动和薄适配分解，不应把新写运动驱动列为默认任务；同时必须把库版本补齐和设备数据质量核查放到联调前，而不是留到最后验收。
