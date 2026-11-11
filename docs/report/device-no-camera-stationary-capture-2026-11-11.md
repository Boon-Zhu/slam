# 无相机静止补测

检查日期：2026-11-11（Asia/Shanghai）。对应 [issue #4](https://github.com/Boon-Zhu/slam/issues/4)，依据[轮次指南](../development/device-capture-round.md)和[控制入口](../development/device-capture-entry.md)，与[首次联合静止录制](device-first-stationary-capture-2026-11-10.md)对照。

本轮无相机录制持续约 121.21 秒，录制期间雷达及反馈连续性明显改善，未重现数秒收录停顿或反馈超时。**雷达退出异常仍复现，整体关闭验收未通过**。编排器报告 `finished`，但只统计 launch 父进程返回码，不能覆盖雷达子进程 `-6`；本报告按子进程原始日志判定。未执行运动，不代表运动、停车或建图验收，也不关闭 issue #4。

## 环境与本轮变化

- 机器人 Pi 5 / Debian 12 arm64，容器 Ubuntu 22.04.4 / ROS 2 Humble / Python 3.10.12；沿用 `yahboomtechnology/ros-humble:3.8` 实际镜像 ID `sha256:7e79c61b64b81311caf297640e5c6fd70279be4cbd38c2c087e8e3395e566047`，不是 registry digest。
- 沿用 `/home/pi/slam-capture-20261110-4d137a4` 的 arm64 构建产物，采集代码基线 `4d137a41f01379f3197dba80720405366e846893`。本机当前 HEAD 为 `bf510b567d982d2e284438b4458c1b1b586e56b0`，两者 `src/` 无差异；部署门禁再次验证实际安装模块、厂商库和雷达配置/二进制哈希。本轮没有重新编译或修改业务代码、厂商驱动及其关闭方式。
- 新容器 `dogzilla-no-camera-20261111`，新持久根目录 `/home/pi/slam-capture-no-camera-20261111`，容器内 `/data/capture`。上一轮 `/home/pi/slam-capture-data-20261110/current` 原件保留，未清理或复用。
- 从配置中移除 camera driver、全部 `/camera/` 声明来源和 `/dev/video0`，容器只映射 UART0/UART1。自动发现后的 bag 也没有图像、压缩图或相机信息话题。保留反馈、状态、metadata、events、`/scan`、`/tf_static`；附加发现 `/parameter_events`、`/rosout`。
- 反馈频率、雷达 launch、5 秒来源中断告警、4 GiB 最小空闲门槛和关闭信号路径保持上一轮设置。相机依赖不再作为准入必需项。配置与新的环境证据适配器保存在本轮部署目录及归档中。
- 重连时机器人已重启，APP PID 1548、OLED 服务重新运行。核对 APP 无 TCP 6000 活动客户后，沿用已有授权只临时停止这两项；没有停用其开机配置。PipeWire/WirePlumber 本轮保持运行，不接管相机。
- 系统时间初始偏离真实 NTP 约 64,268 秒。使用上一轮已验证的实时多源 NTP/SSH 转发重新校时；prepare 检查偏差约 +1.90 ms，结束/导出后约 +4.67 ms，门槛仍为 250 ms。电脑自身时钟未作为参考，电脑验证文件的墙钟时间可能早于机器人封存时间；事件顺序须结合轮次和执行日志，不把跨机墙钟排序当成同步证据。未配置持续 NTP daemon，也不承诺硬件采样时钟同步。

## 实际录制与连续性

轮次：`20261111T110119-67933b8eeecf`。计划录制约 120 秒，正常 finish 探查及关闭带来少量尾部；bag 消息实际跨度 `121.205766873` 秒，共 **6,517 条**，bag 目录 **10,168,324 bytes**，其中消息序列化载荷 **6,385,900 bytes**。

用户在录制后确认：“一直静止，没有搬动”。该现场观察与软件证据分别保存；bag 全部 status 为 READY、`enable_motion=false`、invalid=0、backpressure=0，events 为零。

| 来源 | 消息数 | 实测频率/间隔 |
| --- | ---: | --- |
| `/scan` | 1,220 | header 平均 10.061 Hz，header 最大间隔 0.10163 s；收录平均 10.063 Hz，收录最大间隔 0.16713 s |
| feedback 合计 | 4,080 | 收录平均 33.656 Hz，最大间隔 0.13000 s；无无效记录 |
| read_imu_raw | 2,397 | 返回单调时间平均 19.769 Hz，最大间隔 0.05590 s |
| read_motor | 1,199 | 返回单调时间平均 9.885 Hz，最大间隔 0.10841 s |
| read_battery / roll / pitch / yaw | 各 121 | 各约 0.999 Hz，最大间隔约 1.0065–1.0101 s，符合约 1 Hz 读取设置 |
| status / metadata / events | 1,214 / 1 / 0 | status 最大收录间隔 0.20049 s；events 为非周期来源，零条不伪造事件 |
| tf_static / parameter_events / rosout | 1 / 1 / 0 | 静态快照及实际自动发现来源 |

雷达、聚合 feedback、status 均未出现超过 1 秒收录间隔；recorder 健康文件没有来源中断、告警或 fatal。scan header 到收录的差值中位数 0.09859 s、最大 0.16726 s，含驱动时间语义和收录等待，不直接等于硬件扫描延迟。缺少硬件帧序号参照，不能宣称绝对零丢帧。原始反馈有效性只表示协议与查询归属检查通过，单位、轴向及物理准确度未因此验收。

| 对照指标 | 11-10 联合录制 | 本轮无相机 |
| --- | ---: | ---: |
| scan 最大收录间隔 | 6.797 s | 0.167 s |
| feedback 最大收录间隔 | 5.879 s | 0.130 s |
| bag 内无效反馈/超时 | 5 | 0 |
| vmstat 平均 / 最大 I/O wait | 8.46% / 50% | 0.22% / 2% |
| vmstat 平均 CPU user+system | 约 34% | 4.8% |

本轮 vmstat 为 60 个两秒样本，排除首个开机累计值，无 swap in/out；观察窗口与 bag 首尾不完全重合。结束后温度 51.8°C、`throttled=0x0`，根盘约 30 GiB 可用。两轮属于不同启动会话、不同时间的现场比较，不是严格单变量因果实验；结果支持减轻图像负载能改善当前采集，但不能据此断言 SD 卡损坏或确定此前停顿的唯一根因。

## 退出异常与证据边界

1. recorder、雷达 launch 父进程、入口返回码均为 0；机器人 bag SQLite/metadata/必需来源检查通过，串口 st_rdev 全量扫描在关闭后及容器停止前均确认无人持有。
2. `lidar.stdout.log` 中 `oradar_scan` 收到两次 SIGINT：`1794366222.655676767` 和 `1794366222.660430378`，相隔约 4.75 ms；随后 `*** buffer overflow detected ***: terminated`，子进程退出 `-6`。静态 TF 子进程 `-2`。编排器向进程组发信号、launch 再转发可能相关，但本轮未改变信号路径、未隔离单次 SIGINT，不能认定根因。去掉相机仍复现，说明此次退出异常不依赖相机参与。
3. 入口 `shutdown_audit.success=true`、`worker_exited=true`。关闭时恰有一次 `read_imu_raw` 被中断，审计记录 `invalid_feedback_count=1`、`error=interrupted`，保留原始串口字节及一条未确认入包的反馈；还有 CLOSED 事件未确认入包。这是停止入口时的尾部记录，不是 bag 内反馈超时，不混入录制有效率。
4. 入口 stderr 另有 `The following exception was never retrieved: failed to call timer: timer is canceled, at ./src/rcl/timer.c:249`。进程仍返回 0，硬件线程已退出、串口已释放；该关闭告警保留待调查，不省略为“全程无错误”。
5. 相机未运行，因此没有复验或修复相机退出问题。雷达静态 TF 的 z=0.18 m 未实测，标定、反馈语义及其他全量覆盖项继续保留。

## 导出、回放与保存位置

导出核对 **168 个原始文件**通过，manifest SHA-256：`25584d08264867134596d7d83a3876fdb6292ae03e8f8c1beb91c7892c0bec89`。机器人封存原件未修改，电脑额外分析与现场观察仅写入 `verification/`。

电脑隔离容器实际 `ros2 bag play` 已通过，播放器返回 0，8 个话题的数量、CDR 内容和嵌入时间戳全部匹配；播放器自身生成的 5 条 parameter_events 单独排除。`export_receipt.json` 的 `replay_verified=false` 是导出工具未更新的字段，回放结论以独立 `replay_report.json` 的 `ok=true` 为准。

- 电脑数据：[20261111T110119-67933b8eeecf](../../.local/device-no-camera-2026-11-11/datasets/20261111T110119-67933b8eeecf/)。关键文件：`round.json`、`recorder_health.json`、`bag_check.json`、`lidar.stdout.log`、`entry.stderr.log`、`resources_after.json`、`verification/export_receipt.json`、`verification/replay_report.json`、`verification/quality_analysis.json`。
- 额外执行证据：[.local/device-no-camera-2026-11-11](../../.local/device-no-camera-2026-11-11/)，包括 vmstat、前后校时、容器参数、服务交接、电脑导出适配器及分析脚本。相同补充证据复制到数据集 `verification/session_evidence/`；不改变原始 manifest。
- 机器人原件：`/home/pi/slam-capture-no-camera-20261111/current`。旧真实轮次和本轮均保留，没有 clean。
- 空闲采集容器已停止；临时 NTP relay 和专用 SSH 反向端口已关闭，用户 SSH 主连接保留。APP/OLED 保持停止、OLED 开机配置仍 enabled；桌面媒体服务保持运行。电脑回放容器在验证结束后停止，数据保留。

本轮完成无相机静止数据补采，连续性证据支持后续采用无相机阶段配置。雷达异常关闭、编排器漏报子进程错误和入口关闭告警仍待处理，**本轮未据此自动进入动态采集**；相机补采与 issue #4 全量覆盖要求不变。没有提交、推送或发布 issue 评论。
