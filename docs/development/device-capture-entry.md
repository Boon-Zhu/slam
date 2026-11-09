# 首次采集 ROS 控制与反馈入口

适用：Ubuntu 22.04 / ROS2 Humble / Python 3.10。此入口实现[首次采集方案](../../.scratch/device-first-capture/spec.md)中的临时控制通路；设备依据见[2026-11-08 实机复核](../report/device-first-capture-verification-2026-11-08.md)。它不替代正式 D→C→A 通路，也没有避障、失联停车或自动动作序列。

本组件包括 `dogzilla_capture_interfaces` 与 `dogzilla_device_capture`，前者生成消息/服务，后者提供 `capture_node` 和 `capturectl`。默认只读；启动、退出、重连不会自动站立、复位或执行旧动作。mock 后端的数据明确标记为 synthetic，不是机器狗数据。

## 构建与本地模拟

在已配置的 Humble 开发容器中，从仓库根目录构建：

```bash
source /opt/ros/humble/setup.bash
colcon build --base-paths src --packages-select dogzilla_capture_interfaces dogzilla_device_capture
source install/setup.bash
ros2 launch dogzilla_device_capture capture.launch.py backend:=mock
```

模拟控制测试时显式设置 `enable_motion:=true`。它只作用于 mock，不打开任何设备。所有客户端/录包进程需 source 同一 install overlay。测试和真实后端应使用不同的 `ROS_DOMAIN_ID`；实际操作建议所有进程运行在机器人同一容器，设置 `ROS_LOCALHOST_ONLY=1`，电脑只提供 SSH。

包的 Python 依赖是 ROS 自带运行库及 pySerial；真实后端额外依赖机器人已经安装的 DOGZILLALib。mock 模式不会导入 pySerial 或厂商库。不将设备上的库复制修改后作为本项目实现。

本地工程检查使用 `bash scripts/check-device-capture.sh`，默认工具位于 `/opt/python-tools/bin`，构建、安装与日志放入 Git 忽略的 `.local/device-capture-check/`；可用 `CAPTURE_TOOLS_DIR`、`CAPTURE_BUILD_ROOT` 覆盖路径。脚本执行 Ruff、严格 mypy、colcon build、pytest 和 colcon test。原版库的 PTY 集成测试需安装 pySerial，并通过 `DOGZILLA_VENDOR_SOURCE` 指定未修改的 `DOGZILLALib.py` 路径；未提供时该项会跳过，不能声称原版库适配已经验证。本次无跳过的运行配置与证据见[验收报告](../report/device-capture-entry-acceptance-2026-11-08.md)。

## 真机启动前提

1. 核对当前设备、现场姿态、供电和操作者。正式录制前按方案完成扩容与校时；本组件不会代为修改磁盘、系统时钟或网络。
2. 检查 `ss -tnp` 中 APP TCP 6000 是否有活动操作者；核对 APP 进程完整命令。临时停止 `yahboom_oled.service`，只终止已经核对的 APP Python 进程；保留开机配置。不要使用宽泛的 `pkill python`。
3. 核对控制串口无持有者。`sudo fuser -v /dev/ttyAMA0` 仅作辅助：本机实测它可能漏报容器内的持有者，需同时在宿主 PID namespace 按字符设备 `st_rdev` 扫描 `/proc/<pid>/fd`，确认扫描无权限错误。入口工厂也执行该检查；不要同时启动原装 `yahboom_base`、`yahboom_dog_joint_state` 或 OLED。
4. 用机器人 arm64 环境构建本项目 overlay。电脑 amd64 构建产物不能直接复制到机器人运行。

真实入口要求宿主 PID namespace，以便检查全部设备持有者，并使用共享锁文件避免多个采集容器同时启动。下例假定项目及机器人构建产物已放在 `/home/pi/slam-capture`，只启动只读入口：

```bash
sudo docker run --detach --name dogzilla-capture --init \
  --network none --pid host --cap-drop ALL \
  --cap-add SYS_PTRACE --cap-add DAC_READ_SEARCH \
  --security-opt no-new-privileges --read-only --tmpfs /tmp \
  --device /dev/ttyAMA0:/dev/ttyAMA0 \
  --mount type=bind,source=/run/lock,target=/run/lock \
  --mount type=bind,source=/home/pi/slam-capture,target=/workspace/slam,readonly \
  --env ROS_LOCALHOST_ONLY=1 --env ROS_DOMAIN_ID=24 \
  --env ROS_LOG_DIR=/tmp/ros-log --env PYTHONDONTWRITEBYTECODE=1 \
  --entrypoint /bin/bash yahboomtechnology/ros-humble:3.8 -c \
  'source /opt/ros/humble/setup.bash; source /workspace/slam/install/setup.bash; exec /workspace/slam/install/dogzilla_device_capture/lib/dogzilla_device_capture/capture_node'
```

节点以 detached 容器运行，SSH 或 CLI 断开不会连带结束节点。容器直接 exec 已安装的节点脚本，让 SIGTERM 经 init 转发到节点，不依赖外层 `ros2 run` 进程转发信号。该命令没有数据集持久目录挂载，也没有运行 recorder；完整录制环境另行准备。容器要求能检查 `/proc` 的进程 fd；检查权限不足时入口报告 FAULT，不跳过检查。2026-11-09 真机验证确认：只有 `SYS_PTRACE` 仍不能遍历其他 UID 的 fd 目录，需补充 `DAC_READ_SEARCH` 读取权限；无需 `--privileged`。工厂在硬件线程中创建唯一库对象，检查实际实现源码 SHA-256 为 `3d05141c71b1066e2274cb0d842bd45b328c6d57a9032b7484494433b185585d`，再设置串口排他访问。哈希不匹配需要重新调查版本，不能任意改成当前哈希绕过。

计划进行实际运动时，结束只读入口并在完成现场核对后，以 `--ros-args -p enable_motion:=true` 显式重新启动。新进程会产生新会话 ID，不重放旧请求。复用容器名之前先保存旧容器日志并显式移除已经停止的容器。程序不会自动重启 APP/OLED；厂商 APP 启动可能带动作副作用。

## 操作方式与结果含义

通过另一个 SSH 会话进入同一容器并加载 overlay：

```bash
sudo docker exec -it dogzilla-capture /bin/bash
source /opt/ros/humble/setup.bash
source /workspace/slam/install/setup.bash
ros2 run dogzilla_device_capture capturectl status
```

`capturectl` 提供以下命令。幅度是厂商函数输入，不是 m/s 或 rad/s；实际三档速度和转角要按方案测量。示例参数仅展示语法，不构成已校准运动设置：

```bash
ros2 run dogzilla_device_capture capturectl forward --input 5 --duration 0.6
ros2 run dogzilla_device_capture capturectl left --input 30 --duration 0.3
ros2 run dogzilla_device_capture capturectl right --input 30 --duration 0.3
ros2 run dogzilla_device_capture capturectl stop
```

- 直行幅度整数 1–20，左右转幅度整数 30–70；持续秒数必须有限且大于零。幅度、时长都没有隐式默认值。
- CLI 先获取当前会话，再为每次操作生成请求 ID。节点忙时拒绝新动作；同会话同请求不会执行第二遍，冲突请求与旧会话被拒绝。
- 服务 `accepted=true` 只说明已受理。运动 CLI 继续等待 `MOTION_WRITTEN`；停止 CLI 等待 `STOP_REQUEST_COMPLETED`。这些只表示软件写入结果，输出中的 `physical_state=not_verified` 提醒实际运动/停稳仍需现场观察。
- CLI 返回 0 表示获得所请求的软件结果；返回 2 表示拒绝/失败或发送前未找到入口；返回 3 表示结果未知。未知结果不自动重试，先查看 status/events，避免重复动作。
- CLI/SSH 退出不自动取消动作；已接受的动作继续由机内单调计时结束。需要提前结束时显式调用 `stop`。
- `--namespace /capture/device --timeout 5` 是 CLI 全局选项，放在子命令前。`--timeout` 控制客户端等待，不改变机器人动作时长。

## 数据接口、时间和采样

所有 ROS 名称位于 `/capture/device`：

| 名称 | 类型 | 语义 |
| --- | --- | --- |
| `submit_motion` | `dogzilla_capture_interfaces/srv/SubmitMotion` | 会话、请求 ID、action、magnitude、duration_s；受理结果 |
| `stop` | `dogzilla_capture_interfaces/srv/Stop` | 独立请求 ID；受理结果 |
| `feedback` | `dogzilla_capture_interfaces/msg/Feedback` | 查询类型、序号、完整串口观察字节、厂商值、有效性及错误 |
| `events` | `dogzilla_capture_interfaces/msg/CaptureEvent` | 接受、拒绝、写入、停止、查询暂停、时钟变化与故障事件 |
| `status` | `dogzilla_capture_interfaces/msg/CaptureStatus` | 当前入口状态和统计；READY 不意味着机器人已物理停稳 |
| `metadata` | `dogzilla_capture_interfaces/msg/CaptureMetadata` | 版本、配置、数据来源、固件响应和时间映射 |

`feedback/events` 使用 reliable/volatile；`status/metadata` 使用 reliable/transient-local、保留最新值。动态反馈 `wall_start_ns/wall_end_ns` 是宿主请求/返回系统时间，`mono_start_ns/mono_end_ns` 是本次开机内的单调时间；都不是传感器采样时间。`SerialChunk` 保存 op、单调时间和 bytes，包括被厂商库丢弃的内容。不同开机的单调时间不能直接拼接。`REQUEST_ACCEPTED.detail` 为 JSON，记录 action、magnitude 和 duration_s；`MOTION_WRITTEN.detail` 另记录 motion_start_mono_ns 与 deadline_mono_ns，可核对计划动作时段，仍不能解释为物理运动开始/结束时刻。

`valid` 表示响应通过协议校验、查询归属检查且厂商返回值满足该读取方法的格式要求，不表示传感器样本新鲜度、物理单位或准确性已验收。失败值、额外载荷、未知含义均保留，不能只看 `values` 就当有效样本。关节响应尾部 3 字节、固件 `M-` 前缀在原始 chunks 中；`text/values` 保留厂商返回。当前不发布标准 Imu、JointState、TF 或 odom，防止未核实单位与坐标系被误用。

默认目标读取频率：IMU 20 Hz、关节 10 Hz、电池及独立 roll/pitch/yaw 各 1 Hz；固件启动读取一次并保留到 metadata。启动参数 `<read_method>_hz` 可以调整，参数启动后只读。调度不突发补读，实际间隔以记录为准。队列满时暂停新查询并报告背压，控制仍可执行；恢复后继续，不填补暂停区间。

`use_sim_time` 必须为 false，启动和运行时都拒绝改成 true。系统时间与单调时间差的显著变化会产生事件；停止期限只使用单调计时。串口包装默认查询期限 1 s、单次读等待 5 ms、写等待 50 ms、空轮询等待 1 ms，均在 metadata 披露；这些不是物理停车时延保证。

停止、新运动可打断当前反馈等待，再由同一硬件线程写命令。没有第二个线程与厂商库并发读写。ROS 的服务回调与发布回调使用独立 callback group，多线程 executor 保证发布阻塞时服务仍可提交请求。

## 中断、迟到响应与关闭

协议没有请求序号，因此同地址迟到响应不能天然区分所属查询。中断或超时后，该地址保留未决状态；入口继续接收、记录迟到字节，在归属未解决前不发送该来源的新查询，其他可读来源继续采集。不能把无效占位或迟到数据伪装成新的有效样本。

恢复状态记录在共享锁旁的 `.session` 文件中。进程重启不会默认清掉未决来源；异常退出的恢复会更保守。仅在操作者已经实际重新上电 MCU 后，才可显式传入 `fresh_hardware_session:=true` 声明硬件会话已更新。这个参数不会执行 MCU reset，不能仅因 SSH 重连或想消除错误而使用。

正常收尾顺序遵循 spec：动作调用停止 → 人工核对停稳并保留静止尾部 → 关闭/检查 bag → 退出控制入口及驱动 → 核对资源释放。可用 `sudo docker stop --time 10 dogzilla-capture` 给节点发送 SIGTERM，并在显式删除容器前通过 `sudo docker logs dogzilla-capture` 保存完整 stdout/stderr；示例不使用 `--rm`，以便退出后取回审计日志。入口 SIGINT/SIGTERM 时尝试停止（仅运动启用模式）、关闭串口，不恢复厂商程序；SIGKILL、断电与进程崩溃不在此保证内。

节点退出不会依靠同步 DDS flush 才发送停止。关闭后向 stderr 输出 `shutdown_audit` JSON，包含控制状态、尚未发布的反馈/事件及正在发布而结果不确定的批次；原始字节编码为 hex，非有限浮点保留为 `nonfinite` 文本标记。该尾部明确标为未确认进入 bag，须连同运行日志保存。停止/关闭失败或硬件线程未退出时进程返回非零，不能只因进程结束就宣布停稳或资源释放成功。

## 录制、回放与验证边界

入口不管理 recorder。完整采集器需同时覆盖相机、雷达、事件及其他已可用来源，不能只录本入口就称全量。以下只是本入口的 topic 录制示例，输出应置于已经挂载的宿主持久目录：

```bash
ros2 bag record -o /data/capture-session \
  /capture/device/feedback /capture/device/events \
  /capture/device/status /capture/device/metadata
```

先检查 metadata 中确有固件信息和 backend=vendor，再将正式数据用于交付。record 必须正常 Ctrl-C 关闭并检查 `metadata.yaml`、消息数量及可读性。离线回放只启动消费者：

```bash
ros2 bag info /data/capture-session
ros2 bag play /data/capture-session --clock
```

不要在回放环境启动真实控制入口；反馈和事件本身不驱动运动服务。消费者按项目约定使用回放时间。若需核对每条历史 status，订阅队列要足够大；默认只保留最新状态的深度 1 不能用于完整历史计数审计。

包内测试覆盖纯 CLI 参数、真实 rclpy 服务/反馈/晚加入 metadata、发布阻塞时停止受理、退出停止失败证据、安装后 CLI 子进程，以及 mock 数据的真实 rosbag record→关闭→读取→play→逐话题订阅数量/内容核对。测试不访问机器狗。测试通过不替代机器人上的容器构建、只读接管、实际运动/停车以及首次完整静止录制验收；执行结果以本次验收报告为准。

2026-11-09 已另行完成机器人 arm64 构建、真实反馈只读接入、共享锁/串口排他访问及关闭释放检查，见[真机只读验证报告](../report/device-capture-readonly-verification-2026-11-09.md)。该轮未执行运动、雷达/相机并行采集或正式 rosbag 录制；正式采集仍须补齐持久化与完整录制验证。
