# 首次全量采集：现有接口源码调查

调查日期：2026-11-06。状态：讨论材料，未决定或实施采集方案。只读核对 2026-11-05 下载到本仓库的一手源码；未联网、未访问机器人、未执行厂商模块、未改动上游。历史运行状态以当日系统报告为限，不代表机器人今天状态。本文仅解决方案讨论所需的接入可行性，不追求完成传感器标定或 B 的算法选型。

## 来源定位

以下路径相对 `.scratch/system-audit-2026-11-05/`，行号对应历史快照：

- **APP**：`host/home/pi/DOGZILLA/app_dogzilla/app_dogzilla.py`。
- **Camera**：`host/home/pi/DOGZILLA/app_dogzilla/camera_dogzilla.py`。
- **Lib**：`image/root/DOGZILLALib/DOGZILLALib/DOGZILLALib.py`（3.1.9；历史接口报告记录宿主安装文本与此相同）。
- **Base**：`image/root/yahboomcar_ws/src/yahboom_base/yahboom_base/base.py`。
- **Joint**：`image/root/yahboomcar_ws/src/yahboom_dog_joint_state/yahboom_dog_joint_state/yahboomcar_joint_state.py`。
- **TF**：`image/root/yahboomcar_ws/src/tf_publisher/tf_publisher/tf_publisher.py`。
- **Champ launch**：`image/root/yahboomcar_ws/src/champ_bringup/launch/bringup.launch.py`。
- **Scan**：`image/root/yahboomcar_ws/src/oradar_lidar/src/oradar_scan_node.cpp`（此前接口报告逐段审读的来源）。

项目边界来自 `README.md` §1、§6，以及 `AGENTS.md`：原装硬件和底层步态不改；命令不是实际位移；A 提供原始反馈、B 负责运动估计。历史运行及单位详情参见 `docs/report/dogzilla-system-audit-2026-11-05.md` 和 `docs/report/dogzilla-interface-audit-2026-11-05.md`。

## 1. APP 能避免新增 UART0 读者，但不能提供全部反馈

| 数据 | 一手源码结论 | 对首次采集的影响 |
| --- | --- | --- |
| 电池 | APP 131–140 调用现有 `g_dog.read_battery()` 后 TCP 返回；328–331 的 `02` 分支仅调用该函数；561–564 首次连接也返回电池。 | 能复用现有 APP 实例，无须新增串口实例；不是电压读数已校准的证据。不要用 `0F/0` 代替读命令，因为 310–312 随后 reset。 |
| 关节 | APP 195–214 将12个角度截断为整数再编码；唯一调用入口 `0F/4`（321–323）随后执行 `motor_speed(50)`。 | 存在返回通路，但有写速度参数副作用、精度损失；不能命名为无副作用原始反馈读取。库读失败返回空列表会使 APP 下标访问异常，不能把缺包解释为静止。 |
| IMU | APP 全文没有 `read_imu_raw/read_roll/read_pitch/read_yaw` 调用或对应反馈分支；Lib 587–598 才提供 IMU 读取。 | 不能据此规划“保留 APP/OLED，再由 TCP 无侵入采到 IMU”。若 IMU 是首次全量必需项，UART0 所有权与采集入口必须先选定。 |

APP 是顺序 `accept → recv` 服务（538–594），仅处理当前连接；`listen(1)` 不是多客户端遥测广播。记录器占用连接时不能假定手机 APP 仍可独立控制。TCP 接收每次只取最后一个 `$...#`（573–578），也不能直接把它当成熟流式 RPC。上述是源码约束，吞吐与丢包仍待实际测量。

库构造即打开串口并清空缓冲（Lib 122–126），每次读请求也清空缓冲并发请求（150–158）。因此新增独立“只读”DOGZILLA 对象依然争用设备。历史系统报告记录 APP/OLED 已同时打开 UART0；“不新增读者”也不等于已经实现唯一所有者。

**需要讨论的唯一核心分叉：** 若全量必须包含 IMU/较原始关节反馈，需要在采集期间协调 APP/OLED 等 UART0 使用者，由一个明确所有者串行读取和执行被授权的控制；若暂保留现有 APP 路径，只能承认 IMU 缺失及关节路径副作用。前者是方案候选，不是已授权停服务或已实现适配器。

## 2. HTTP 摄像头读取有模式前提，不能只写一个 URL 就算解决

- `/video_feed` 仅创建 `mode_handle()` 响应（APP 660–665），本身不调用 TCP 初始化或运动方法。与 `/init`（668–671 调用 `init_tcp_socket()`）不同；后者 g_init 已真时返回，否则启动 TCP 线程（597–614），不应当通用健康检查。
- APP 默认 `g_mode='Home'`（40），TCP 断开时也回到 Home（591–594）。只有 Standard/Fullscreen 模式才读取并发帧，其他模式一直 sleep（629–651）。因此 HTTP 200/连接建立不代表收到摄像头帧。
- `0F/1`、`0F/2` 分支返回界面缓存、切模式（313–318），这些分支本身没有运动调用；但需要占用并保持 TCP 会话，与控制客户端如何复用仍要确定。
- APP 启动即创建摄像头（34）；HTTP 读失败会触发 reconnect（634–640）。Camera 65–82 会重开视频设备、失败时在0/1之间切换，特定状态下重设配置；所以 HTTP 读取不能承诺绝无摄像头设备副作用。
- 输出为叠加 FPS 文本并重新编码的 JPEG（APP 642–647），不带采样时间、序号或标定；可以作现场观察资料，不能宣称未加工原始相机图像或硬件同步图像。
- 不应为“激活视频”随意重启 APP：启动末尾 `motor_speed(50)`、`action(14)`（692–695）。

**方案分叉的联动：** 若为 IMU 暂停 APP 并转移 UART0 所有权，现有 HTTP 服务同时失去提供者；摄像头需要独立的采集路径。不能把“关闭 APP 解决串口冲突”和“继续使用 APP HTTP 摄像头”同时写入默认方案。

## 3. odom 只能登记为待发现，不能把未证实来源列为必有输入

Base 全文（1–57）只有 Twist 订阅和库运动调用，没有 Odometry 发布；Joint 37–47 只创建关节/IMU发布者；TF 13–32 仅发布固定数值的 base_footprint → base_link。这些不能证明实际位移来源。

工作区有 CHAMP 候选：Champ launch 124–131 声明 cmd_vel estimation 的 odom TF 选项、close_loop_odom 默认 false；167–214 引用 champ_base state_estimation 与 robot_localization EKF，并重映射 odom/local、odom。这只能证明存在启动文本和候选依赖，不证明节点正在运行、依赖完整、接入实际反馈，亦不证明其 odom 就是纯命令积分。未执行这些入口。

因此首次采集方案可以要求记录实际发现的 odom/TF 发布者及消息，若无则明确 unavailable；不应为填满清单临时启动另一套步态或制造零值 odom。没有可用 odom 不阻塞原始设备采集方案确定；它阻塞“已有可信里程计”结论以及依赖其质量的 B 验收。

## 4. 可保留原值与未知标记、不必先解决的项目

以下为建议的证据语义，不是已经定下的数据格式：

| 未知/缺陷 | 首次采集可怎样保留 | 不能越界声称 |
| --- | --- | --- |
| IMU gyro 单位、轴向、yaw参考；关节反馈物理含义 | 保存库返回原数组、库版本/来源、读取起止时间，标记单位/物理含义未验证。Lib 564–598 已有换算，因此“库原始返回值”不等于 UART 原始字节。 | 不直接标成合格 ROS SI 数据或真实编码器反馈，不在此阶段强制完成标定。 |
| 库失败占位 | 电池0、IMU全零标记成功性不明；关节[]单独记录；异常及超时与数值分开。Lib 485–514、587–598。 | 不能从全零推断有效静止，不能从零电池推断确认没电；不伪造可从该返回值恢复的 valid。 |
| 激光0/NaN、角度重排、scan_time语义 | 保存原 LaserScan 和接收时间，附无效值统计与已知驱动语义。接口报告 §2 对应 Scan 108–188、321–348。 | 不先修上游或填充缺测；时间字段不是已验证的束采样时刻。 |
| 未测外参/TF冲突 | 保存来源模型、候选TF及其发布者；区分未测几何和实测几何。 | 不为“全量”启动冲突TF，也不把历史URDF当实测外参。 |
| 相机帧无硬件时间/有叠字 | 记录接收时刻与获取路径，标明MJPEG观察帧。 | 不作为严格同步/无损原始视频。 |
| odom缺失或来源不明 | 记录未发现/来源未知；若发现则保留来源证据和原消息。 | 不把 cmd_vel、关节或姿态直接改名为实际位移。 |

可以先确定方案而后通过短时采集测得频率、丢包、串口读取代价、录像码率、同步偏差与数据质量。执行前仍需核实资源所有权、路径实际可用性、存储空间及收尾方式。历史 MS200 退出 buffer overflow 尚未解决，必须进入采集失败/收尾讨论；这里不据猜测诊断根因，也不要求把所有质量未知都预先消除。
