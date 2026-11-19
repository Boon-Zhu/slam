# 无相机数据包与离线复现

编写于 2026-11-18，描述 2026-11-11 交付版。模块开发入口见[总览](device-motion-data.md)。

## 1. 定位并验证交付包

仓库的[动态采集报告](../report/device-motion-stage-capture-2026-11-11.md#5-交付与收尾)记录了当前项目副本位置。`.local/` 属于本地工作区。跨机器交接使用 `slam-stage-data-20261111.tar.gz` 和随附的 `.sha256` 文件，从解压根目录的 `README.md` 开始。先在两文件所在目录核对归档 SHA-256，再解压到独立工作目录。

```bash
sha256sum -c slam-stage-data-20261111.tar.gz.sha256
```

| 路径（相对解压后的 `slam-stage-data-20261111/`） | 内容与用途 |
| --- | --- |
| `README.md` | 接收方环境、读取命令、现场限制和事故摘要 |
| `datasets/20261111T110119-67933b8eeecf/` | 无相机静止基线，121.2058 s，6,517 条消息。用户确认全程静止、无人搬动，适合静止扫描和反馈解析 |
| `datasets/20261111T162132-97e6f5fe7058/` | 最终动态，562.9012 s，30,285 条消息，bag 目录 46,381,065 bytes。用于运动扫描和五段事件回归 |
| `diagnostics/20261111T160737-0a0bb8ea0bd4/` | 首次准备有雷达进程但零扫描，含 probe、串口和退出证据。无 bag、无前进或转向 |
| `diagnostics/20261111T161316-6f84a91173f0/` | 中间动作和 recorder 锁冲突。保留失败 bag 和事故观察。故障后的约 30 cm 动作缺少正常录包，最终主样本的约 33 cm 是另一轮动作 |

## 2. 根据问题查找轮次文件

以下路径相对所选轮次目录。无 bag 的诊断轮次只包含其已经产生的文件。

| 要查的问题 | 文件与判读 |
| --- | --- |
| 怎么读取原始数据 | `bag/metadata.yaml` 列出 SQLite3 存储、主题、消息类型、CDR 格式和数量，`bag/bag_0.db3` 保存序列化消息及收录时刻。从完整的 `bag/` 打开 |
| 哪一轮、以什么配置运行 | `DATASET.md` 说明轮次布局。用 `round.json` 查 ID、模式、会话、接受缺失、准备/收录回执及进程退出码。用 `config.json` 查准备配置，用 `recording_config.json` 查实际来源及自动发现项 |
| 准备、开始和结束时采到了什么 | 用 `{prepare,start,finish}_probe-*.json` 及同名 stdout/stderr 查各阶段探查，用 `timeline.jsonl` 和 `supervisor.log` 找轮次状态迁移，用 `recorder_health.json` 查成功交给 writer 的收录计数、中断及 `closed`/`fatal` |
| 数据库能否读取 | `bag_check.json` 检查 SQLite、metadata、必需话题覆盖、数量和错误。协议级 payload 有效性由下方分析资料提供 |
| 由哪个软件和设备环境产生 | `deployment.json`、`deployment_files/` 和部署日志保留环境、参数、源代码、厂商文件哈希/快照。用 `handoff/` 和 `resources_{before,after}.json` 核对交接与资源，用 `clock.json` 和 `clock_*.log` 核对校时 |
| 怎样核对类型与采集实现 | `packages/dogzilla_capture_interfaces/` 是该轮的消息/服务 schema 与构建入口。`packages/dogzilla_device_capture/docs/` 是采集指南快照，`capture_source/` 是可加载的同版本工具源码。离线读取只需要接口包和必要 ROS 依赖 |
| 数据文件是否完整 | `manifest.json` 记录原始文件集合、大小和 SHA-256。`verification/export_origin.json` 记录导出来源，`verification/export_receipt.json` 记录副本哈希检查。`manifest.json` 自身和 `verification/` 不在原始文件集合内 |
| 实际回放有无匹配 | `verification/replay_report.json` 查 `ok`、播放器返回码、各话题数量和 CDR 摘要，`replay.log` 查实际 argv。导出回执中的 `replay_verified=false` 是该工具独立写入的初始值，历史回放结论读取独立报告 |
| 怎样选择片段或检查有效值 | `verification/quality_analysis.json` 查时间、间隔和反馈分类，动态 `scan_payload_check.json` 查点数和范围。动态 `motion_segments.json` 查请求、事件和窗口，`operator_observations.json` 查现场描述，`acceptance_review.json` 查当时交付范围 |
| 怎样追查未进 bag 的异常 | 查看 `entry.stderr.log` 的 `shutdown_audit`、`lidar.stdout.log`/`lidar.stderr.log`、`recorder.*.log`，再按需查看 `verification/session_evidence/`。其中包含跨轮次现场日志、分析脚本和部署证据，按轮次 ID 归属。`diagnostics/*/verification/session_incident_observations.json` 保留对应异常观察 |

## 3. 核对话题和时间轴

| 话题 | 类型 | 静止 / 动态数量 |
| --- | --- | ---: |
| `/scan` | `sensor_msgs/msg/LaserScan` | 1,220 / 5,647 |
| `/tf_static` | `tf2_msgs/msg/TFMessage` | 1 / 1 |
| `/capture/device/feedback` | `dogzilla_capture_interfaces/msg/Feedback` | 4,080 / 18,966 |
| `/capture/device/events` | `dogzilla_capture_interfaces/msg/CaptureEvent` | 0 / 25 |
| `/capture/device/status` | `dogzilla_capture_interfaces/msg/CaptureStatus` | 1,214 / 5,630 |
| `/capture/device/metadata` | `dogzilla_capture_interfaces/msg/CaptureMetadata` | 1 / 1 |
| `/parameter_events` | `rcl_interfaces/msg/ParameterEvent` | 1 / 15 |
| `/rosout` | `rcl_interfaces/msg/Log` | 0 / 0 |

- **收录时间**来自 recorder 回调中的宿主墙钟，用于 bag 读取、回放和查找已交付窗口。`bag_first_ns` 是 bag 首条消息的收录时刻。
- **消息时间**由各来源定义。扫描 header 由驱动在等待整帧前写入，设备事件的 `wall_ns` 描述宿主侧事件，反馈的 `wall_start_ns` 和 `wall_end_ns` 描述宿主请求与返回。分析时注明使用了哪个字段。
- **单调时间**用于同一开机内的软件动作时长、查询间隔和超时。用同一请求的事件 `mono_ns` 差得到写入至停止写入时长。静止与动态来自不同开机，不跨轮拼接单调时钟。采集端经过 NTP 校时，归档验证机墙钟可能偏移，跨机顺序以轮次记录和流程关系为准。

收录时间的实现见 [recording.py](../../src/dogzilla_device_capture/dogzilla_device_capture/recording.py)，扫描与串口时间详见[设备接口](device-motion-data-device.md)。

## 4. 重建动态窗口

用 `verification/motion_segments.json` 中的 `request_id` 关联 `/capture/device/events`。每个请求有 `REQUEST_ACCEPTED`、`AXES_CLEARED`、`MOTION_WRITTEN`、`MOTION_DEADLINE`、`STOP_WRITTEN`。窗口从写入事件的 `wall_ns` 减 2 秒，到停止写入事件的 `wall_ns` 加 2 秒，按扫描的 **bag 收录时间**选取。事件自身的 `recorded_ns` 用于审计事件被收录的时刻，两种时间会有偏差。

| 片段 | 厂商输入 / 计划 s | 软件窗口（相对 bag 起点，s） | 窗口扫描 | 现场观察约值 |
| --- | --- | --- | ---: | --- |
| 1 直行 | 5 / 5 | 51.740–60.741 | 90 | 33 cm |
| 2 直行 | 10 / 5 | 149.455–158.455 | 90 | 66.5 cm |
| 3 直行 | 15 / 2 | 263.477–269.477 | 61 | 34 cm |
| 4 左转 | 30 / 1 | 364.644–369.645 | 50 | 15° |
| 5 右转 | 30 / 2 | 466.964–472.964 | 60 | 60° |

上表窗口四舍五入到毫秒。复现时直接取 JSON 的整数纳秒边界。例如第 1 段 `request_id=e6d226a9-85f1-45a0-a2fc-d439a69ac0de`，从 bag 首条到 `MOTION_WRITTEN.wall_ns` 相隔约 53.740 s，软件写入到停止写入历时约 5.0011 s。接收方可以筛出 90 帧验证窗口。现场约值用于了解场景，精确起步/停稳、测量参考点和误差均待补证据。需要建立跨窗口轨迹的实验应读取整轮连续数据，并将等待段纳入分析。

## 5. 读取和回放

从可写的解压副本根目录操作。`archive verify` 会刷新导出回执，`archive replay` 会刷新回放报告。原始交付的 `verification/` 留作历史证据。运行随包工具时设置 `PYTHONDONTWRITEBYTECODE=1`，避免在封存目录产生未列入 manifest 的 `__pycache__`。

```bash
dataset="$PWD/datasets/20261111T162132-97e6f5fe7058"
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="$dataset${PYTHONPATH:+:$PYTHONPATH}"
python3 -m capture_source.archive verify --directory "$dataset"
```

上面的哈希核对只需 Python。运行 ROS 播放时进入独立的 Ubuntu 22.04 / Humble / Python 3.10 环境，加载包内接口定义。以下命令在同一工作副本及 shell 中继续执行，要求 `colcon`、Humble 基础环境、`rosbag2_py`、`ros2bag` 和包内接收说明所列 ROS 依赖。

```bash
source /opt/ros/humble/setup.bash
colcon build --base-paths "$dataset/packages/dogzilla_capture_interfaces"
source install/setup.bash
export ROS_LOCALHOST_ONLY=1
export ROS_DOMAIN_ID=87
ros2 bag info "$dataset/bag"
python3 -m capture_source.archive replay --directory "$dataset"
```

使用当前主机上空闲的 domain，播放器与消费者放在同一隔离环境。归档回放将记录话题重映射至随机前缀，并按数量和序列化字节逐话题核对。静止 `events` 和两轮 `rosout` 的期望数量为零。交付时动态通过 5 倍速的同类验证，以上命令使用默认原速。仅对已关闭并导出的副本做 SQLite/离线分析，活动录包用健康文件或 ROS 订阅查看。模块消费回放另外按 D 的[回放配置](device-motion-data-integration.md#回放配置)运行，以便验证 TF、ROS 时间和模块输出。

在同一 shell 中可用随包脚本复算动态动作窗口和每段扫描覆盖。脚本写入工作副本的 `verification/motion_segments.json`。

```bash
python3 "$dataset/verification/session_evidence/analyze_motion_segments.py" \
  "$dataset" "$dataset/verification/operator_observations.json"
```

本步骤完成时，应有轮次 ID、manifest 哈希、bag 可读和数量核对结果。执行了 ROS 核对时，再记录新生成的 `replay_report.json` 的 `ok`、返回码和逐话题结果。针对具体模块追加的输出与运行配置保存到实验目录。
