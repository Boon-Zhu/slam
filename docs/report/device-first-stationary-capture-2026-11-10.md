# 首次静止采集与磁盘扩容实测

检查日期：2026-11-10（Asia/Shanghai）。对应 [issue #4](https://github.com/Boon-Zhu/slam/issues/4)，执行依据为[控制入口](../development/device-capture-entry.md)、[轮次指南](../development/device-capture-round.md)及本地首次采集 spec。代码基线 `4d137a41f01379f3197dba80720405366e846893`。

本轮完成磁盘在线扩容，并执行首次真实联合静止录制。**静止采集验收未通过**：已观察到收录间隔、原始图像缺帧及驱动退出异常。文件可读、哈希一致或实际回放通过均不能替代连续性与场景质量验收。没有发送运动指令，没有开启运动轮次，没有关闭 issue。

## 1. 磁盘扩容

用户确认备份可恢复、供电稳定并明确允许扩容后执行。当前分区表及卡头前 4 MiB 另存电脑；独立 systemd 一次性任务执行，避免 SSH 断开中断操作。

| 对象 | 扩容前 | 扩容后 |
| --- | --- | --- |
| SD 卡 `/dev/mmcblk0` | 62,534,975,488 bytes | 不变 |
| p1 起始/大小 | sector 8192 / 1,048,576 sectors | 不变 |
| p2 起始 | sector 1,056,768 | 不变 |
| p2 大小 | 62,914,560 sectors，30 GiB | 121,081,856 sectors，57.7363 GiB |
| 根文件系统可用量，`df -h` | 约 5.1 GiB | 扩容后约 32 GiB，采集后约 30 GiB |
| ext4 block count，4 KiB/block | 7,864,320 | 15,135,232 |

`sfdisk --no-act` 预演后只延伸 p2 末端，使用 `partx --update --nr 2` 更新内核视图，再执行 `resize2fs`。任务 `Result=success`、`ExecMainStatus=0`，分区表验证无错误，内核确认在线扩展成功；无需重启。根 UUID `f382bc55-e740-48d8-8770-2a65d2dc2900`、磁盘标识 `0x738162de` 和根挂载保持不变。挂载中文件系统状态不等同于离线 fsck 验收。

用户所述 Windows 备份目录实际为 `E:\robot-backups\dogzilla-20261109-before-expand`。本轮只读检查发现 `card.img.partial` 长度等于整卡容量，但 `status.json` 明确记录全量源卡哈希验证由用户暂停；不能将其描述为本轮已独立验证的可恢复镜像。扩容是在用户确认可恢复的前提下执行，未修改备份文件。

扩容证据见本地 [.local/device-first-capture-2026-11-10](../../.local/device-first-capture-2026-11-10/) 的 `partition-before.sfdisk`、`card-first-4mib.bin`、`expand-root.sh`、`expansion-result.log`。机器人副本在 `/home/pi/slam-storage-expansion-20261110`。

## 2. 校时、部署与资源交接

- 机器人经 Wi-Fi SSH 操作，所有采集 ROS 进程运行于同一机器人容器，`ROS_LOCALHOST_ONLY=1`、`ROS_DOMAIN_ID=24`。真实镜像为 `sha256:7e79c61b64b81311caf297640e5c6fd70279be4cbd38c2c087e8e3395e566047`，保留原厂镜像及库。
- 新 arm64 工作区 `/home/pi/slam-capture-20261110-4d137a4` 独立构建两个 package 成功。持久采集根目录 `/home/pi/slam-capture-data-20261110` 映射到容器 `/data/capture`。源码包 SHA-256 为 `9cb5bd2e4349cb188abcc349649296de0e0075a70762803c87036982907eb3d7`。
- 机器人初始时间仍为 11-04，systemd-timesyncd 无有效时间源；电脑时间也比公共 NTP 源慢约 61 秒。不能把电脑墙上时钟直接作为同步成功依据。
- 本地部署适配器通过 SSH loopback 转发实时 UDP NTP 查询；电脑仅转发报文，不提供自身时间。至少两个公共源返回有效响应且彼此偏差不超过 150 ms，网络延迟须小于 400 ms；采用最低延迟样本，prepare 入口要求偏差不超过 250 ms。初次校正后最低延迟样本偏差约 -4.8 ms，实际 prepare 再校时并保存证据。容器只为显式校时额外授予 `SYS_TIME`。这不是持续 NTP 锁定或设备硬件采样时钟同步。
- 用户分别授权临时停止 APP/OLED 及 PipeWire/WirePlumber/socket。APP PID 1417 已停止，OLED 通过宿主 systemctl 停止；媒体服务及 socket 通过 pi 用户 systemd 停止，均保留开机配置。本轮不自动恢复。
- 交接过程暴露：新数据目录权限需要按容器实际 UID 设置；厂商镜像缺少 `ss`；容器中的 systemctl 返回成功不能证明宿主服务停止。保留这些失败记录，最终改为宿主实际停服务、容器按 `st_rdev` 全量复查设备；UART0、UART1、video0 均无持有者后才 prepare。

## 3. 配置与采集结果

首个 prepare 轮次 `20261110T162229-0a56ab348ee4` 在部署检查失败：pySerial 3.5 实际是 Python distribution，不是 `python3-serial` Debian 包。没有启动驱动或录制。149 个证据文件导出并通过清单/哈希验证后，经用户明确授权执行 clean；电脑副本保留。后续配置按实际包来源查版本，不绕过依赖检查。

真实静止轮次：`20261110T162513-9b883385a677`。所有声明来源均通过 start 探查，`accepted_missing=[]`。运动开关始终为 false。相机采用设备实际支持的 640×480、30 fps、YUYV 原始格式，ROS 编码 `yuv422_yuy2`，每帧 614,400 bytes。准备阶段独立订阅 147 帧，接收频率约 29.20 Hz；预览可辨认室内物体。

用户在录制后明确确认：“一直静止，没有搬动”。该观察作为现场静止标签，与软件运动开关证据分别保留。

图像传输插件额外宣告 compressed、compressedDepth、theora 话题，自动发现逻辑将其纳入录制；订阅还使压缩插件实际工作。没有以压缩图替代原始图，但这些额外消费者会影响并行负载，后续应单独调查。compressedDepth 对当前彩色来源没有消息，不能称为已采集深度。

| 来源 | 落盘消息数 |
| --- | ---: |
| 原始反馈 | 2,908 |
| 入口状态 / metadata / events | 913 / 1 / 6 |
| `/scan` | 916 |
| `/camera/image_raw` | 2,197 |
| `/camera/camera_info` | 2,634 |
| `/tf_static` | 1 |
| compressed / theora | 2,633 / 2,636 |
| compressedDepth / parameter_events / rosout | 0 / 1 / 0 |
| 合计 | 14,846 |

最终 bag 消息跨度约 91.11 秒；现场原计划约 60 秒，实际持续时间以 bag 为准。目录约 1,733,759,169 bytes。recorder 正常退出 `0`，metadata 与 SQLite 数量一致，数据库及 payload 可读，声明必需来源均非零。此检查不证明无丢帧。

## 4. 已发现的问题和边界

1. 录制中多个来源出现超过 5 秒的收录间隔：原始图像最大 6.790 秒、camera_info 6.807 秒、scan 6.797 秒、反馈 5.879 秒。**scan 的 header 间隔最大仅 0.1046 秒**，因此不能把收录端停顿说成雷达停止出帧。78 秒 vmstat 观察窗口内，39 个两秒样本的平均 I/O wait 约 8.46%，最大 50%，无 swap in/out；CPU user+system 平均约 34%。与写盘等待有关是待验证解释，尚不能据此断言 SD 卡硬件损坏或锁定根因。
2. 原始图像实际入包平均约 24.15 Hz。按共同时间范围的 header 对齐，2,633 个已收录 camera_info 对应时刻中，436 个没有原始图像，约 16.56%；原始图像没有独有而 camera_info 缺失的时刻。这个比例以已收到的 camera_info 为参照，不是硬件曝光总数的绝对丢帧率。原始图像 header 最大间隔 1.580 秒；camera_info header 最大间隔 1.548 秒。需分别调查源端间隔与收录端缺帧。
3. 相机进程收尾返回 `-11`（SIGSEGV）。雷达 launch 父进程返回 0，但子进程 `oradar_scan` 在 SIGINT 后报告 `buffer overflow`、退出 `-6`；静态 TF 子进程退出 `-2`。父进程成功不能覆盖子进程异常。
4. 入口退出码 0，`shutdown_audit.success=true`、硬件线程退出；最终累计 invalid_feedback_count=5，`last_error=timeout`。bag 中也有 5 个无效反馈：read_motor 3 次、read_imu_raw 1 次、read_pitch 1 次，均为 timeout。6 条 events 均为 `FEEDBACK_SCHEDULE_SKIPPED`，没有运动事件；status 全部为 READY、enable_motion=false、backpressure=0。入口保持 READY 不等于全部反馈始终有效，也不等于物理停车验证。
5. 本轮状态为 `finished_with_errors`。结束后 UART0、UART1、video0 的所有者均为空，没有自动恢复厂商服务。
6. 相机没有有效内参文件，厂商静态 TF 的 z=0.18 m 没有实测；IMU/关节的单位、轴向和物理含义不因成功入包而自动得到确认。此轮不是运动或停车验收。

另外，图像 header 到入包时间差中位数约 0.558 秒、最大 7.391 秒；scan 对应中位数约 0.101 秒、最大 6.797 秒。该差值包含驱动时间戳定义及传输/收录等待，不能直接解释为硬件曝光或扫描延迟。部署快照保留了 usb_cam 实际安装版本的时间换算头文件，后续据此进一步核实。

## 5. 导出、回放与后续

无线导出及电脑实际回放均已通过。导出核验 174 个原始文件，manifest SHA-256 为 `28b060705cf8d640071157da38aee8ae96baa38d2ed1333926227dac4536e9bc`。实际 `ros2 bag play` 返回 0，13 个话题的接收数量、CDR 内容哈希及嵌入时间戳全部匹配；三个零消息话题保持为零，播放器自身 5 条 parameter_events 单独识别并排除，没有伪造成原始数据。

电脑完整副本：[20261110T162513-9b883385a677](../../.local/device-first-capture-2026-11-10/datasets/20261110T162513-9b883385a677/)。主要证据为 `verification/export_receipt.json`、`verification/replay_report.json`、`verification/quality_analysis.json`。导出回执只证明文件传输及哈希，其 `replay_verified=false` 字段未由回放函数更新；回放结论以独立 `replay_report.json` 的 `ok=true` 为准。现场观察及外部运行日志另存 verification 下，不修改已封存原始文件。

机器人原件仍保留于 `/home/pi/slam-capture-data-20261110/current`，没有对本次真实轮次执行 clean。末次现场设备扫描再次确认两个串口及相机无持有者，随后停止本轮空闲采集容器；临时 NTP relay 和专用 SSH 反向端口已关闭，用户 SSH 主连接保持。APP/OLED、PipeWire/WirePlumber 及相关 socket 仍按授权保持停止，开机配置未禁用。下轮准备需重新建立校时通路。

大文件传输期间另一次校时探查因网络延迟超预算而失败，没有据此声称时钟合格；传输完成后两个实时 NTP 源通过，最低延迟样本偏差约 -9.6 ms。保留失败及复测证据；仍不声称持续 NTP 服务已配置。

电脑实际使用隔离 network/IPC 的 Humble 容器及同基线构建接口，复用用户认证的 SSH control socket。本机传统 SCP 对远程 `current/.` 报 `unexpected filename: .`；仅对此固定来源使用本地 wrapper 切换 SFTP，保留主机密钥与文件名验证，不改项目归档器。首次失败导出的 `.partial-*` 保留。

电脑镜像缺少自动发现的 Theora 消息包，已在独立容器从官方 Humble apt 下载并解压到本轮目录，不修改宿主或机器人。机器人为 2.5.1，电脑为 2.5.5；两者实际 Packet.msg 完全一致，SHA-256 为 `d0a11f3d0e3f11652c81236b4be503378b8cbe78bdfb0145a227df6f2faaac8f`。类型支持序列化往返及本轮真实 2,636 条 Theora 消息回放均通过。这只验证消息兼容，不表示编码器版本或行为相同。

下一步应先定位原始图像缺帧、写盘停顿及上游驱动退出问题，再决定补录。不得直接进入运动轮次或将 issue #4 标为完成。本轮没有修改业务代码、提交、推送或发布 issue 评论。
