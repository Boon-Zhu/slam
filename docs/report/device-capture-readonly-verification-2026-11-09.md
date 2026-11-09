# ROS 入口真机只读验证

检查日期：2026-11-09（用户时区 Asia/Shanghai）。依据[首次采集 spec](../../.scratch/device-first-capture/spec.md)、[入口实现验收](device-capture-entry-acceptance-2026-11-08.md)及[使用指南](../development/device-capture-entry.md)。

结论：已完成机器人 arm64 构建、真实串口反馈读取、共享锁/串口排他访问和退出释放验证。发现并修正了部署命令的权限缺项；运行时代码和厂商库未修改。未执行运动、停止运动指令、正式全量采集或 rosbag 录制。

## 版本、授权与操作边界

- 部署代码固定为 `d166af69637619dfe646bbb76df4b1031ff6b132`，分支 `feature/device-capture-entry`，只传输两个 ROS package 的源码；与用户另一个对话的采集脚本开发隔离。
- 源码 tar SHA-256：`5b98d4c4d8d6acbe85d30d691529ae4b241d445430648d7eb525f2611c8ddbf3`。机器人端校验一致，在独立目录 `/home/pi/slam-readonly-20261109-d166af6` 构建。
- 机器人宿主为 Debian / aarch64；厂商 Humble 镜像 ID 为 `sha256:7e79c61b64b81311caf297640e5c6fd70279be4cbd38c2c087e8e3395e566047`，Python 3.10.12、pySerial 3.5。
- 实际 DOGZILLALib 3.1.9 实现源码 SHA-256 为 `3d05141c71b1066e2274cb0d842bd45b328c6d57a9032b7484494433b185585d`，与已核实版本一致。构造函数仅打开/清理串口缓冲并初始化解析状态。
- 经 Wi-Fi SSH 操作；初始 APP PID 1404、OLED PID 1898 占用 UART0，没有 TCP 6000 活动操作者。用户在本轮直接确认“允许临时停用，继续只读验证”后，临时停止 OLED 服务和已核对的 APP 进程；保留厂商文件、开机配置，不自动恢复。
- 所有设备节点显式传入 `backend=vendor`、`enable_motion=false`；没有创建运动或停止服务客户端。验证脚本只订阅 ROS 数据，检查串口发送帧为读取类型 `0x02`。只读验证允许主机部署、诊断文件写入及经确认的临时服务交接，不代表宿主文件系统完全无改动。

## 构建及首轮故障

无设备映射的原装 arm64 容器中 `colcon build` 成功构建两个包，耗时 17.6 s。随后在独立无设备容器导入运行时依赖，验证五种自定义消息的实际序列化/反序列化和两种服务导入，默认 `enable_motion=false`。

机器人系统时间仍错误地处于 **2026-11-04**；源码归档时间晚于机器人时钟，因此 tar/make 报 future timestamp / clock skew。构建使用全新目录，没有沿用旧增量产物，之后导入和真机运行通过；本轮没有校时，也不将这些 wall timestamp 当作准确日历时间。

首轮沿用原指南的 `--pid host --cap-drop ALL --cap-add SYS_PTRACE`，入口在打开串口前进入 FAULT：

```text
initialization_error: cannot_inspect_host_fds: host preflight/permissions required
```

故障时 feedback_count=0，退出码 1。进一步在不映射串口的容器中定位到 `/proc/692/fd`：该目录属于 UID 997 的 `systemd-timesyn`，`SYS_PTRACE` 不能替代目录读取权限。

补充 `--cap-add DAC_READ_SEARCH` 后，无设备诊断可完整遍历可见宿主 fd；随后原样代码成功接管设备。保持原有占用检查和最小设备映射，未使用 `--privileged`、未跳过权限失败。已更新使用指南的部署示例。

## 60 秒真实反馈

第二轮节点会话 `082fb390-94da-427e-b050-5c2a5c856533`。订阅观察持续 **60.015 s**，收到 2,020 条动态反馈、601 条状态、1 条元数据；状态始终 READY，enable_motion=false，无效计数和背压计数均为零。固件通过校验，库返回 `4.0.1-Y`，完整响应保存在原始 chunks。

实际频率按每个来源首末请求单调时间计算 `(N−1)/(t_last−t_first)`；查询耗时为宿主请求至返回的单调时间差，不是 MCU 采样或通信硬实时保证。

| 来源 | 有效/总数 | 实际 Hz | 最大请求间隔 ms | 查询耗时中位/最大 ms |
| --- | --- | --- | --- | --- |
| IMU raw | 1187/1187 | 19.773 | 55.805 | 4.672 / 7.317 |
| 关节 | 593/593 | 9.887 | 109.047 | 4.590 / 6.569 |
| 电池 | 60/60 | 0.999 | 1006.652 | 3.442 / 4.827 |
| roll | 60/60 | 0.999 | 1007.572 | 3.463 / 5.112 |
| pitch | 60/60 | 0.999 | 1010.487 | 3.399 / 5.505 |
| yaw | 60/60 | 0.998 | 1009.462 | 3.415 / 4.969 |

电池按厂商百分比口径，主观察窗口为 **46–51**，首值 47、末值 49；不解释为电压或精确剩余续航。IMU 数值有变化，关节 12 个厂商解析值及本轮 yaw 值保持不变；这不足以确认传感器芯片、单位、轴向、标定或物理准确性。

动态反馈 sequence 为 **36–2055 连续**。观察者在节点启动后加入、在节点关闭前退出，因此它收到的 2,020 条不等于节点整个生命周期的 2,110 次查询；窗口内没有序号缺口，不对窗口外作接收完整性承诺。元数据使用 transient-local，可以晚加入读取；本窗口没有接收到 events，不表示节点未产生启动事件。

窗口内动态反馈与元数据固件包含 4,042 个 `write_request`/`write` chunks（一个发送通常记录两次），检查均为合法地址的读取请求，没有运动类型写入。原始字节及有效性保留，不仅保存厂商解析值。

## 排他访问、重开及关闭

发现宿主 `fuser -v /dev/ttyAMA0` 在真实节点运行时仍返回空。这是本轮证实的工具可见性限制，不能据此断言容器没有持有串口。使用与适配器一致的字符设备 `st_rdev` 检查补核，设备号为 **204:64**。

为验证这一缺口，第三轮以同一版本重新启动只读入口，沿用同一共享锁及恢复路径，没有使用 `fresh_hardware_session`。10.001 s 窗口收到 **337 条有效反馈**、101 条状态、1 条元数据；sequence **43–379 连续**，状态始终 READY，未见无效样本。该窗口电池厂商百分比为 **43–46**，最后一次观察值为 **46**；不将两轮变化解释为已校准的放电速率。

运行时按设备号扫描得到唯一持有者 PID 39192、fd 15，完整命令确为 `capture_node ... enable_motion:=false`，扫描没有权限错误；竞争获取共享 flock 被拒，受限容器内第二次以只读方式打开 UART 返回 **EBUSY**。这些检查没有向串口发送数据。

两次成功运行均以 SIGTERM 正常关闭，容器退出码 0，`shutdown_audit` 显示 worker_exited=true、success=true、CLOSED；未出现 STOP/MOTION 写入。60 秒轮次最后有 1 条尚未发布的有效反馈，原始字节保留在 stderr 审计，明确未确认进入 bag；10 秒补核轮次没有未发布反馈。

最终宿主扫描确认设备持有者为空、无扫描错误；共享锁可重新获取，`.session` 未决查询标记不存在。锁文件本身保留是正常现象，不等于锁仍被持有。

## 留给采集脚本的已验证约束

1. 真实入口容器采用 `--pid host`、共享 `/run/lock`、`SYS_PTRACE` **及 `DAC_READ_SEARCH`**；启动后检查实际 READY、backend=vendor、enable_motion 与固件有效性，不能只检查进程存在。
2. 设备交接/释放不能只依赖 `fuser` 空输出；按设备号确认持有者并披露检查权限失败。
3. 将 recorder/观察者的实际覆盖区间与节点生命周期区分；若要保留启动 events，应在流程设计中保证订阅就绪，不能假定晚加入能获得 volatile 历史事件。
4. 保留节点完整 stderr/stdout，正常关闭后核对 `shutdown_audit`。DDS 已发布、recorder 已落盘及审计尾部是不同状态，本轮最后一条未发布反馈是实际例证。
5. 正式采集前仍需完成扩容、校时、宿主持久目录、雷达/相机接入及 bag 关闭/读取/回放验证；本轮只读诊断 JSONL 不冒充首次正式静止片段。

## 证据与最终设备状态

本机证据位于 Git 忽略的 `.local/device-readonly-2026-11-09/`：

- `preflight.log`、`handoff.log`、`build.log`、`import-check.log`：设备状态、交接、构建和依赖核查。
- `proc-check*.log`：缺失目录读取权限的定位及修正验证。
- `run-readonly*.log`、`run-ownership.log`：三轮启动结果。
- `robot-evidence/evidence/`：首轮未打开串口的失败证据。
- `robot-evidence/evidence-readable/`：60 秒原始 ROS JSONL、状态、节点退出审计。
- `robot-evidence/evidence-ownership/`：10 秒补核及设备号、锁和串口排他证据。
- `feedback-summary.json`：逐来源频率、间隔、值范围和关闭摘要。
- `robot-evidence/evidence-sha256.txt`：机器人生成的 25 个证据文件哈希，Wi-Fi 取回后 **25/25 校验一致**。
- `final-state.log`：最终资源、服务、容器及磁盘状态。

机器人原件、源码及 arm64 构建产物保留在 `/home/pi/slam-readonly-20261109-d166af6`，总计约 14 MiB；没有自动删除。仅移除本轮三个已经停止且日志已保存的临时容器，最终没有运行中的 Docker 容器。

APP Python 进程和 OLED 服务保持停止；APP 的原终端外壳仍存在。OLED 开机配置仍为 enabled，未卸载或永久禁用，也没有为恢复服务触发可能的预设动作。根分区仍为 30 GiB，可用约 5.1 GiB，未扩容；系统时钟未同步。没有启动或测试雷达、相机，没有运动或实际停车验收，没有执行厂商服务自动恢复、Git 提交/推送或 issue 关闭。
