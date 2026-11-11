# 分步采集、导出与回放

创建于 2026-11-09。运行目标 Ubuntu 22.04 / ROS 2 Humble / Python 3.10。本工具落实首次采集 spec Q27–Q44；它与[现有控制入口](device-capture-entry.md)组合，运动仍由操作者逐段调用 `capturectl`。本轮实现和验证使用 **synthetic/mock**，不代表机器人雷达、相机、校时、无线导出或运动已通过联调。

## 构建与文件

沿用入口指南的 colcon 构建并 source overlay。`dogzilla_device_capture` 新增 `capture-round`、`capture-round-archive`；也可通过 `python3 -m dogzilla_device_capture.round_session` 与 `.archive` 调用。运行依赖 `rclpy`、`rosbag2_py`、`ros2bag`、`rosidl_runtime_py`、`sensor_msgs` 和 PyYAML，列于 package.xml，不修改上游。

- `config/round_synthetic.json`：明确的无硬件配置，mock 反馈、8 点模拟 scan、16×16 RGB 图；不改系统时间，不访问设备。必须同时传 `--synthetic`，产物显著标记 synthetic。
- `config/round_vendor.json`：真机部署模板，**不能原样通过准备**。它保留待现场确定项，不能用合成来源顶替缺失来源。
- `round_config.py` / `round_session.py`：配置验证、独立后台 supervisor、每轮状态和资源收尾。
- `recording.py`：真实 ROS 订阅和 rosbag2 writer；`archive.py`：文件检查、哈希、导出、实际 ROS 回放。

机器人只使用持久挂载根目录的 `current/`；每轮的 `round_id` 唯一。命令参数 `--root` 应为绝对路径且每次一致。不要把数据放在容器临时文件系统；不要为采集使用自动随 SSH 会话删除的容器。后台进程使用独立 session，SSH/CLI 退出不会关闭正在录制的轮次；容器停止、断电、supervisor 被 SIGKILL 是另外的故障边界。

## 真机配置与准备门禁

先完成独立构建和部署，再填写本轮 JSON 配置。工具不安装驱动、不改上游，也不检查是否扩容。容量预算 `minimum_free_bytes` 和超时 `timeout_s` 必须显式填写；模板数值只是示例，须根据实际图像/雷达/反馈写入量及停止等待确定。

1. **校时**：配置 `clock.sync_command` 和 `clock.verify_command` 为 argv 数组。提供的 `round_preflight clock-sync` 使用现有 chronyd 的 `chronyc makestep`、`waitsync`；`clock-check` 解析实际 `chronyc tracking`，输出 `synced/source/offset_s/stratum/raw_tracking`。仅在显式运行时操作系统。历史证据未证明机器人已安装/配置 chrony，部署负责人需先核对可信时间源、权限及宿主 daemon socket。不要在容器内另造一个时钟同步成功。也可配置其他已验证的宿主适配命令，验证 stdout 必须是同结构 JSON。`max_offset_s` 无默认值，按实际对时要求和测量确定。校时失败、未同步、无时间源、非有限偏差或超预算均拒绝准备。
2. **部署**：`deployment.expected_files` 填实际运行代码、入口/雷达/相机配置和未修改厂商库的绝对路径及 SHA-256；`expected_image` 填实际运行镜像 ID。`environment_command` 输出 `{ "ok": true, "image": "sha256:…", "versions": {...} }`。提供的 `round_preflight environment` 读取由宿主 `docker inspect --format '{{.Image}}' <当前容器>` 生成且只读挂载的镜像证据，并用 `dpkg-query` 检查逐个 `--package` 的真实已安装版本。证据必须针对当前容器，不能复用旧文件。完整配置、实际哈希/版本和源码快照随轮次交付；`expected_files` 中外部驱动/相机配置的实际内容保存在 `deployment_files/`，映射写入 deployment.json。
3. **资源交接**：先核对 APP 连接、完整进程命令及 OLED 服务；只显式停止已确认的占用者。保留服务开机配置，不使用宽泛 `pkill python`。可使用下面的显式 handoff 工具；`prepare` 不暗中停止厂商程序。`devices` 列控制 UART、雷达 UART 和实际摄像头设备。工具按字符设备 `st_rdev` 扫 `/proc/*/fd`，拒绝任何占用或权限不完整；需要宿主 PID 视图和既有指南中的 `/proc` 读取权限。结束后重复检查。空 `fuser` 不是释放证据。
4. **驱动**：`drivers` 为具名 argv 列表，按顺序启动；`{round_dir}`、`{motion}`、`{python}` 为受限文本替换，不隐式执行 shell。入口使用实际 vendor 后端，并核对 READY、有效固件、运动开关及同一会话。源码证据支持 `oradar_lidar/ms200_scan.launch.py` 候选；原版退出异常仍需现场复验。
5. **相机**：历史 package index 只证明存在 `usb_cam` 条目，当前仓库没有该部署版本的配置源码。模板将 ROS `usb_cam_node_exe` 和 `FILL_VERIFIED_CAMERA_YAML` 作为待部署核实入口；先在实际镜像核对包版本、executable、参数描述、设备支持的 pixel format、分辨率/帧率、话题名与帧时间语义。未确认参数就失败，不使用 APP 视频、不自动降低质量、不填合成图。图像按 `sensor_msgs/msg/Image` 进入 bag，`camera_info` 等实际发布来源也会纳入。

准备的实际顺序为：创建未覆盖的 current（若存在最近 handoff，则要求该次成功并保存证据） → 自动校时并验证 → 部署哈希/镜像/依赖证据 → 存储可写与预算/设备所有权 → 启动入口和驱动 → 核对入口/来源 → prepared。已有 current 时，任何 prepare 请求都先拒绝，不执行校时或重启。任何准备失败均保留本轮配置、日志和错误，完成已启动进程的收尾；先导出，再按清理条件处理。

`round_handoff` 是独立显式操作，配置 `handoff.inspect_command`（记录厂商当前状态）和 `handoff.stop_commands`（已核对的具体 argv）。调用 `python3 -m dogzilla_device_capture.round_handoff --root /data/capture --config /data/capture-config.json`，保存每条输出及资源复核；存在 current 时拒绝执行。prepare 默认读取 `handoff_latest.json`，拒绝最新失败尝试并复制最新成功证据；也可用 `handoff_evidence` 显式指定证据目录。没有默认 APP PID，不自动恢复 APP/OLED。

## 操作清单

以下命令在机器人已 source overlay 的持久容器内执行，由电脑经 Wi-Fi SSH 发起。SSH 示例仅表达入口，容器启动/挂载/权限先按现场配置完成。

```bash
# 第1轮：静止。prepare和start都不下发运动。
capture-round --root /data/capture prepare --config /data/capture-config.json
capture-round --root /data/capture start
# 重连先查询；不要重发start或之前的动作。
capture-round --root /data/capture status
# 人工已观察停稳，且已经留足所需静止尾部后：
capture-round --root /data/capture finish
```

`start` 会重新探查。缺失来源默认拒绝，输出精确话题；接受时为每项传一次 `--accept-missing /camera/image_raw`，必须与当前缺失集合完全一致。不能借此绕过校时、部署、入口 READY/固件/后端/运动开关或存储门禁。已接受项、探查证据、开始请求时间、recorder 自己的首条收录时间均保存。

每次 prepare/start/finish 探查使用带独立请求 ID 的 JSON 和日志，失败或超时不会读取上次 READY 报告；旧报告保留供追溯。

开始时额外枚举已有发布者的 ROS 话题，连同声明来源写入 `recording_config.json`，不只录预先猜测的业务输入。其他话题采用实际发现的 QoS；多类型冲突拒绝开始。轮次中不自动启动新来源；需事先启动全部预期驱动，额外来源缺少消息时在健康报告明确显示 count=0，不据此宣称全量覆盖。

只有 recorder 的订阅实际匹配，且需消息的每个预期来源至少 `writer.write` 成功一次，才返回 `recording` 回执。status/metadata 用 transient-local 获取快照；events 只要求匹配订阅，静止期间可为零事件。Humble Python 没有新版本 subscription 匹配计数方法，薄适配调用安装版本 librcl 的公开匹配计数 API，已用实际 ROS/SQLite 核对。`writer.write` 返回证明接收/写入路径，不代表已经最终落盘；关闭后再次检查。

首轮导出并实际回放通过后，由操作者按清单进入第二轮：

```bash
capture-round --root /data/capture prepare --config /data/capture-config.json --mode motion
capture-round --root /data/capture start
# 看到recording成功回执后，各动作仍人工调用既有capturectl；参数按现场测量确定。
ros2 run dogzilla_device_capture capturectl status
# 需要提前结束当前动作时：
ros2 run dogzilla_device_capture capturectl stop
# 动作完成、人工停稳观察及尾部录制之后再finish。
```

运动轮次不会读取静止报告作为门禁；未传 `--mode motion` 默认禁止运动。三档直行及左/右转在同一连续运动轮次逐项触发，不自动连续动作。不增加现场逐项标记要求；外部视频按 round_id 关联，事后整理实测参照和片段，人工搬动之间的不连续区间明确注明，无法对应保留未知。

## 状态、异常与结束

- `status`（别名 `stat`）只读，不重发动作；显示 supervisor 身份、状态、当前 recorder 健康、计数和来源告警。PID 必须连同 `/proc` 启动标识匹配，后台不可确认时报告 unknown。
- 单个周期来源超过其显式 `stale_after_sec` 无数据：保存中断起止时间、告警，继续其余来源；不自动停止或重启驱动。非周期事件和快照不因安静而宣称中断。
- recorder 异常退出、writer 异常：调用既有 `capturectl stop` 一次并保留 stdout/stderr 和执行结果；停止发送成功与物理停稳分别报告。状态 failed，拒绝重新 start；不自动恢复录包。写盘满可能无法保存最后错误，仍先尝试 stop；此前文件和 stderr 作为残留证据。
- 正常 `finish` 会重新读取入口；待执行/正在执行动作、入口失联或会话改变均拒绝。成功执行顺序：SIGINT recorder → metadata/SQLite 完整性、消息数量及覆盖检查 → 停驱动/入口 → 保存完整 stdout/stderr（含入口 shutdown_audit）→ 设备释放核对 → manifest 封存。文件检查失败仍收尾，最终 `finished_with_errors`，不是正常完成。
- 入口故障等导致正常 finish 无法成立时，可显式 `abort` 尝试 stop 并异常封存。它不是停稳确认，不恢复 APP/OLED。后台不可达时先人工核对与释放进程、设备，再 `seal-orphan`；此命令要求本轮记录的进程身份均已消失且设备无人持有，只封存异常证据，不发送动作或续录。
- 进程无法有序退出时升级 SIGTERM/SIGKILL 并记录错误，不能把强制退出当作正常 bag 关闭。无法保存最终文件/manifest 时保留 current，人工处理空间或文件系统问题后核对再封存，不覆盖旧数据。

收尾检查整个驱动进程组，即使启动器已退出也继续停止同组子进程。仍有活跃成员或无法核实退出时，继续尝试其他驱动的收尾，但拒绝封存；`seal-orphan` 也检查遗留进程组。驱动应以前台进程运行，不自行脱离进程组成为 daemon。

## 每轮独立导出、电脑验证与显式清理

在**电脑**的 Humble 环境安装同一版本工具与自定义消息包后执行：

```bash
capture-round-archive export --source user@robot:/host/persistent/capture/current --destination /computer/datasets
capture-round-archive verify --directory /computer/datasets/ROUND_ID
capture-round-archive replay --directory /computer/datasets/ROUND_ID
```

导出不会覆盖电脑同 ID 目录；中断副本保留为 `.partial-*`。manifest 记录完整文件清单、大小及 SHA-256，核对缺失、增加和内容变化。哈希成功与实际回放分别报告；实际回放由 `ros2 bag play` 发布到唯一隔离前缀，消费者逐话题核对数量、序列化内容哈希及可解析的时间字段，不向原始控制/设备话题发布。静止 events=0 明确报告，不伪造事件。

数据集包含 bag、round/config/recording_config、部署/校时/资源证据、来源探查与健康、中断/错误、日志、实际自研模块快照、自定义消息/服务及 package 版本、`DATASET.md`。接收者应将 `packages/dogzilla_capture_interfaces` 作为对应版本接口包构建并 source，再使用同版本项目工具回放。该目录含实际消息/服务定义、package.xml 和 CMakeLists.txt；完整入口与轮次使用指南同时位于 `packages/dogzilla_device_capture/docs/`。不依赖采集者工作区使用归档工具时，在已加载对应接口 overlay 后，可执行 `PYTHONPATH=/computer/datasets/ROUND_ID:$PYTHONPATH python3 -m capture_source.archive replay --directory /computer/datasets/ROUND_ID`，使用随包交付的相同工具源码。头时间戳和反馈请求/接收时间的语义沿用入口指南；指令或软件写入不能证明物理位移。数据可读取不等于单位、轴向、标定及全量覆盖已经核实。

导出验证产生 `verification/export_receipt.json`。每次验证先撤销旧成功回执，只有本次完整检查通过才重新生成成功回执；失败或中断时不能沿用旧结果。完成最后一次电脑验证后，把当前回执复制到机器人 current **之外**，显式执行：

```bash
capture-round --root /data/capture clean --receipt /data/receipts/ROUND_ID.json
```

clean 要求已封存、ID/manifest 匹配、原件仍与清单一致及导出副本的成功回执；未导出/校验失败/未显式 clean 都不能复用 current。异常轮次也先导出。不自动删除电脑副本，不自动恢复 APP/OLED。回放报告保存在 `verification/`，不改已封存原始证据；是否可作为首批数据交付还需按缺失与场景质量分别判定。

clean 在与 prepare 共用的生命周期锁内核验轮次及哈希，再删除原件；并发操作返回忙，不自动重试。回执是校验时刻的证据，电脑无法跨机撤销已另行复制的旧文件；重新验证失败后不得使用此前传到机器人的旧回执。

## 无硬件验证

从项目根目录在已配置的 Humble 开发镜像中执行 `bash scripts/check-capture-round.sh`。该脚本运行 Ruff、严格 mypy、两个包 colcon 构建/测试及旧入口回归，端到端产物保存于 `.local/capture-round-check/e2e/`，测试日志以 `check-<UTC时间>-<PID>.log` 留于同根目录；原版库 PTY 回归需按入口指南显式设置 `DOGZILLA_VENDOR_SOURCE` 并提供 pySerial，未配置该可选输入时会跳过，不能报告为全覆盖通过。验证容器所有 ROS 进程在同一隔离 network/IPC 中；本机本轮观察到 host network+host IPC 的 DDS graph 可见但消息不到的问题，不把它解释为机器人已出现相同故障。

仅运行示例流程时可使用 `round_synthetic.json` 配合 `prepare --synthetic`。测试只验证软件路径；实际 arm64 联调、真实校时、资源接管/释放、雷达退出、usb_cam版本/帧参数、并行写盘负载与丢帧、Wi-Fi中断/导出及实际运动停稳均需单独现场验证。
