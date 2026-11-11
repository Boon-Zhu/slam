# 无相机动态阶段采集与交付

执行日期：2026-11-11（Asia/Shanghai）。对应 [issue #4](https://github.com/Boon-Zhu/slam/issues/4)。用户明确同意：先交付动态阶段数据供后续模块开发，已知退出问题后续定位。依据[采集入口](../development/device-capture-entry.md)、[轮次指南](../development/device-capture-round.md)和[无相机静止补测](device-no-camera-stationary-capture-2026-11-11.md)。

**已产出并实际回放验证一轮雷达动态阶段数据**：三档直行、左转、右转及各段等待过程在同一连续 bag 中。可用于扫描接口、离线回放和相关算法开发；不代表完整多传感器数据、速度/转角标定、地图质量或正式运动保护验收。相机未启用，原始 IMU 与关节反馈在本动态轮次均无效，必须按下文限制消费。issue #4 未关闭。

## 1. 环境与范围

沿用 Pi 5 / Debian 12 arm64 宿主，厂商 Ubuntu 22.04.4 / Humble / Python 3.10.12 容器，实际镜像 ID `sha256:7e79c61b64b81311caf297640e5c6fd70279be4cbd38c2c087e8e3395e566047`，不是 registry digest。复用 `/home/pi/slam-capture-20261110-4d137a4` arm64 构建和未修改厂商库/雷达，源码包 SHA-256 `9cb5bd2e4349cb188abcc349649296de0e0075a70762803c87036982907eb3d7`，采集基线 `4d137a41f01379f3197dba80720405366e846893`；当前仓库 HEAD `bf510b567d982d2e284438b4458c1b1b586e56b0` 与该基线的 `src/` 无差异。

机器人容器 `dogzilla-motion-20261111`：host network/PID、独立 IPC、`ROS_LOCALHOST_ONLY=1`、domain 24、cap-drop ALL 后仅补 SYS_PTRACE/DAC_READ_SEARCH/SYS_TIME，共享 `/run/lock`，只映射 UART0/UART1，不映射相机。新根目录 `/home/pi/slam-capture-motion-20261111`；两轮静止原件和本次所有失败/补录原件均保留，未 clean。

设备在静止补测后再次重启；重新核对 APP PID 1534 与 OLED 后按已有授权临时停止，保留开机配置。用户确认正常站立、有人监控、起初周围约 3 米空余，后续逐段反馈位移和剩余空间。每段单独下发，未自动连续执行整套动作。现场明确确认最终补录全过程无人搬动。

每次准备重新使用多源 NTP 校时。初始机器人偏差约 16,829 秒，结束后复查约 +0.82 ms；未以电脑墙钟为参考。电脑验证回执时间可能早于机器人封存时间，不能用未同步的跨机墙钟推断执行顺序。未配置持续 NTP，也不承诺硬件采样时间同步。

## 2. 最终阶段数据与片段

主动态轮次 **`20261111T162132-97e6f5fe7058`**，机器人原件在新根目录 `recapture/current`。消息跨度 **562.901 秒**，**30,285 条消息**，bag 目录 **46,381,065 bytes**。约 9 分钟连续录制包含大量逐段等待时间；动作仅如下五段。

下表起点相对 bag 首条收录时间；时长是软件运动写入至到时停止写入的时段，不能视为实际起步/停稳时刻。现场值来自用户报告，未提供统一参考点、测量误差或跨线时间。

| 片段 | 指令输入 / 计划秒数 | 起点（s） | 软件写入至停止（s） | 用户现场观察 |
| --- | --- | ---: | ---: | --- |
| 1 直行 | 5 / 5 | 53.740 | 5.0011 | 约 33 cm |
| 2 直行 | 10 / 5 | 151.455 | 5.0006 | 约 66.5 cm |
| 3 直行 | 15 / 2 | 265.477 | 2.0002 | 约 34 cm；因前方只确认余量超过 1 m，缩短持续时间 |
| 4 左转 | 30 / 1 | 366.644 | 1.0009 | 约 15° |
| 5 右转 | 30 / 2 | 468.964 | 2.0007 | 约 60°；用户明确要求右转时长翻倍 |

每段在 bag 中均有 REQUEST_ACCEPTED、AXES_CLEARED、MOTION_WRITTEN、MOTION_DEADLINE、STOP_WRITTEN，共 25 条事件。对应请求 ID、原始事件、前后各 2 秒的扫描窗口和现场描述位于 `verification/motion_segments.json`。五个窗口分别含 90、90、61、50、60 帧 scan；窗口内最大收录间隔均小于 0.115 秒。

**这些是三个输入档位的动作样本，不是 spec Q26 所要求的三个行进区间速度测量值。** 没有收到两条线间距与同一机身参考点的跨线时间，不计算或拟合已校准的输入→速度曲线。左/右转测量时长不同且只有现场估计，不能假设转向比例对称；转动伴随平移的大小未知。外部视频此前已要求拍摄，但截至本轮交付未收到或验证文件，列为待补参照，不声称视频存在或已关联。

## 3. 数据有效性及验证

| 来源 | 条数 | 消费限制 |
| --- | ---: | --- |
| `/scan` | 5,647 | `sensor_msgs/msg/LaserScan`，`laser_frame`；约 10.037 Hz，收录最大间隔 0.15882 s、header 最大间隔 0.10307 s，无倒序、无超过 1 秒收录间隔 |
| `/capture/device/events` | 25 | 软件受理/写入/到时停止证据，不是实际轨迹真值 |
| status / metadata | 5,630 / 1 | READY 不代表所有反馈有效；status 中保留无效计数 |
| `read_imu_raw` | 11,130 | **全部 valid=false**，`attribution_uncertain_pending_response`；不能用于 IMU 融合 |
| `read_motor` | 5,587 | **全部 valid=false**，同上；不能用于关节/里程计估计 |
| battery / roll / pitch / yaw | 563 / 562 / 562 / 562 | 本轮协议有效；物理单位、轴向、精度及融合适用性仍待核实 |
| `/tf_static` | 1 | 原厂 `base_link → laser_frame`，z=0.18 m 未实测，不是标定结果 |
| parameter_events / rosout | 15 / 0 | 自动发现来源 |

原始 IMU 和关节未决状态与此前关闭中断、恢复标记有关，原始错误及空值保留；没有删除标记或冒称 MCU 已重新上电。不把无效反馈当成新的硬件样本。话题持续有消息不等于 payload 有效，这也是后续准备门禁需进一步细化的事项。

最终 recorder 返回 0，`recorder_health` 的 fatal、interruptions、warnings 均为空，closed=true；SQLite/metadata/必需话题覆盖检查通过。扫描 header→收录差值中位数约 0.09888 s、最大 0.15898 s，包含驱动时间定义与收录等待，不等同纯硬件延迟。扫描数值检查见 `verification/scan_payload_check.json`，仍不证明标定或地图正确。

导出核对 **169 个原始文件**通过，manifest SHA-256：`cb2b461ca09e8a7aea67d934c832e50a4f1a28edd0f66da1f396af286131616e`。电脑隔离容器实际 ROS 回放使用播放器原生 `--rate 5`，8 个话题的消息数量、CDR 内容及嵌入时间戳全部匹配，播放器返回 0。部署用小型 PATH 适配器只为该固定离线路径增加回放速率，保留全部原校验；实际 argv 在 `verification/replay.log`。导出回执中的 `replay_verified=false` 未被归档器更新，回放结果以独立 `replay_report.json` 的 `ok=true` 为准。

## 4. 本次异常、责任与保留证据

### 首次准备没有扫描

轮次 `20261111T160737-0a0bb8ea0bd4`：入口 READY，但 120 秒准备探查和独立 6 秒 best-effort 订阅均为 `/scan` 0 条。现场确认雷达正常旋转。唯一占用者为雷达进程，实际 UART1 参数 230400/8N1；内核接收帧错误和 break 累计增加。无前进或转向指令、未启动 recorder。结束节点、保留原件后同硬件配置重新准备，扫描恢复；6 秒复查收到 61 帧。只能报告重新打开设备后恢复，尚未确定接线、设备状态或驱动初始化等根因。

### 中间录包锁冲突及一次操作失误

轮次 `20261111T161316-6f84a91173f0`：先执行输入 5、0.5 秒，用户看到移动但难以量测。随后 recorder 因 `writer.write /scan: SQLite error (5): database is locked` 失败。此前助手直接对正在写入的 SQLite 做只读分析，可能与写入锁竞争；该检查方法已停用，所有后续数据库分析均在正常关闭和导出之后进行。

助手随后运行的本地健康断言失败，但 shell 命令串没有阻止后续已获用户授权的输入 5、5 秒动作。这是助手执行流程失误，不能归为厂商驱动问题。该动作返回 MOTION_WRITTEN，助手随后补发 stop 并取得 STOP_REQUEST_COMPLETED；用户明确确认已停稳、位移约 30 cm。由于 recorder 当时已失败，**该 5 秒动作不是可用的录包片段**，不能与最终补录的 33 cm 片段混淆。

后续使用独立部署脚本 `checked_motion.py`：在同一流程检查轮次身份/状态、实际 recorder 进程身份、健康新鲜度、扫描/反馈/status 收录、入口会话与空闲状态，然后只调用一次运动 CLI。失败路径检查覆盖录包失败、过期/缺失来源、会话改变、检查异常；4 个本地测试通过。它防止本次 shell 继续执行的失误，不是正式 C 模块保护，也不能消除检查后状态变化或验证物理停稳。该脚本、测试和哈希均随证据交付；未修改仓库业务 package。

### 退出问题仍存在

最终轮次虽然编排器为 `finished`、launch 父进程为 0，雷达子进程仍在两次 SIGINT（约隔 3.79 ms）后 `buffer overflow` / -6，静态 TF 子进程 -2。入口 audit.success=true、worker_exited=true，但仍有 timer canceled 告警；关闭时的 STOP_WRITTEN/CLOSED 尾部事件明确不保证入 bag。两串口最终持有者为空，空闲容器已停止。**阶段交付不表示整体关闭验收通过。**

接收方流程另行实测：只构建随包 `dogzilla_capture_interfaces`，仅加载 Humble 基础环境和该新 overlay，成功导入数据集中的 `capture_source.archive` 并完成副本哈希校验。首次导入产生 pycache 导致文件集合检查拒绝；接收方说明已补上 `PYTHONDONTWRITEBYTECODE=1`，仅清理测试副本中新生成的两个 pyc 后复验通过，原始数据未改。

## 5. 交付与收尾

- [阶段交付压缩包](../../.local/device-motion-2026-11-11/delivery/slam-stage-data-20261111.tar.gz)：无相机静止基线、最终动态数据、自定义接口/工具快照、接收方 README、动作窗口及限制；两个中间轮次放在 diagnostics，保留错误调查证据。
- [动态数据目录](../../.local/device-motion-2026-11-11/datasets/20261111T162132-97e6f5fe7058/)；[现场观察](../../.local/device-motion-2026-11-11/recapture-observations.json)；[执行证据](../../.local/device-motion-2026-11-11/)。额外材料只写 `verification/`，不改已封存原始 manifest。
- 机器人各轮原件均保留：`/home/pi/slam-capture-motion-20261111/{current,retry1/current,recapture/current}`。APP/OLED 仍临时停止、开机配置未禁用；媒体服务未接管。空闲采集容器、临时 NTP relay/SSH 转发已停止，用户 SSH 主连接保留。
- 用户可先将阶段包交给后续模块；本次未发送给其他成员、未发布 GitHub 评论、未提交或推送。完整覆盖、原始 IMU/关节恢复、物理语义/标定、外部视频与正式运动保护继续另行验证。
