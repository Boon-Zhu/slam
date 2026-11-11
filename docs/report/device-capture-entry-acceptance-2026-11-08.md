# 首次采集 ROS 入口实现与本地验收

日期：2026-11-08。分支：`feature/device-capture-entry`，起点 `develop` / `b853b70e240e57aaef81fd91c708698aeed9fd4b`。代码仍为工作区变更，未提交、推送或部署。

结论：本次最小 ROS 控制与反馈入口的软件实现通过本地验收；独立审查发现的问题均已修复。此结论不代表真机运动、实际停车或首次全量采集完成，不能据此关闭 issue #4。

## 范围与交付

依据[首次采集 spec](../../.scratch/device-first-capture/spec.md)及[设备复核报告](device-first-capture-verification-2026-11-08.md)，实现临时的电脑 SSH → 机器人 ROS 服务 → 未修改厂商库 → MCU 通路。正式 D→C→A 通路、障碍保护和断线停车不在本次实现内。

| 交付 | 内容 |
| --- | --- |
| [dogzilla_capture_interfaces](../../src/dogzilla_capture_interfaces/) | 五种消息、运动与停止两个服务；包含原始串口字节、厂商值、有效性、会话及双时钟时间。 |
| [dogzilla_device_capture](../../src/dogzilla_device_capture/) | 单硬件线程控制器、厂商适配、ROS 节点、`capturectl`、mock 后端、配置和 launch。 |
| [检查脚本](../../scripts/check-device-capture.sh) | 两包构建、格式/静态检查、pytest、colcon test；构建产物与日志默认置于 `.local/`。 |
| [使用指南](../development/device-capture-entry.md) | 构建、操作、资源交接前提、消息含义、录包及关闭审计说明。 |

默认只读，运动需显式启用。直行、左转、右转使用明确输入与持续时间；一次只接受一个动作，不排队、不自动重试、不因重连续跑。动作期限由机器人进程的单调时钟控制。运动/停止的串口写入成功与实际运动/停稳分别表述。

串口资源检查、共享锁和排他访问集中在工厂入口。控制与停止优先于查询；被打断或超时的查询保留原始字节与归属未知状态，同地址未决状态跨进程恢复。协议无请求序号的事实没有被软件隐藏。退出优先处理停止，再输出未确认进入 bag 的尾部审计；停止失败不能以成功退出掩盖。

## 分工与独立审查

三个实施子代理分别负责消息/控制核心、厂商串口适配、ROS/CLI/录包验证；另一个子代理独立检查。主代理集成、复核关键路径、补齐修复并对最终工作区执行完整验收。

独立报告保存在[本地审查记录](../../.scratch/device-first-capture/implementation-review.md)。三项主要发现及闭环：

1. 退出停止失败曾丢失证据且返回成功：补充故障状态、stderr 关闭审计和非零退出；正常/失败两种真实子进程 SIGTERM 回归通过。
2. 底层写异常的实际发送字节数未知，曾可能重新查询并误收迟到响应：将未知写入结果列入未决归属，并保留恢复状态；注入“请求已发送后报错”回归通过。
3. bag 事件曾不含请求时长与停止期限：接受及写入事件增加 JSON 参数，记录写入完成后的单调起点与 deadline；核心与真实录包/回放回归通过。

收尾另补充 CLI 发送/等待/取响应/等待执行事件四处异常的“结果未知”处理，保留请求 ID，不重试或取消；独立增量检查的四项回归也通过。审查结束时未发现仍需阻塞本次软件验收的具体缺陷。

## 最终验证环境与结果

主代理在本机 `slam-humble-desktop:local` 容器执行，架构 x86_64，Ubuntu 22.04 / Humble / Python 3.10.12；工具为 Ruff 0.17.4、mypy 2.4.1、pytest 8.4.2。容器无网络、无物理设备映射，使用独立 ROS domain 74 和 localhost 通信。

pySerial 3.5 来自本地 wheel，安装到容器临时路径；原版库测试直接加载既有审计快照中的 `DOGZILLALib.py`，SHA-256 为 `3d05141c71b1066e2274cb0d842bd45b328c6d57a9032b7484494433b185585d`。PTY 测试使用真实 pySerial 和未修改库，对端为软件模拟响应，不是 MCU。

| 最终检查 | 结果 |
| --- | --- |
| Ruff 检查及格式 | 通过；17 个 Python 文件格式符合要求。 |
| strict mypy | 通过；9 个运行时代码文件无问题。 |
| colcon build | 2 个包成功；关闭 bytecode 生成产生的提示不影响构建。 |
| 直接 pytest | **80 passed，0 skipped**，8.03 s。 |
| colcon test / test-result | **80 tests，0 errors，0 failures，0 skipped**。与上一行是同一套测试的两种运行入口，不相加计数。 |

覆盖内容包括会话/去重/忙状态、时钟变化、动作写入后计时、查询中断/迟到/校验失败、实际 pySerial PTY、发布阻塞时 stop、安装后的 CLI、SIGTERM 退出，以及真实 rosbag record → 正常关闭 → 读取 → play → 消费者计数/内容核对。

最终模拟 bag 实物额外经主代理读取 SQLite 检查，`integrity_check=ok`；共 **41 条**，feedback 27、events 5、status 8、metadata 1。测试使用随机隔离命名空间 `/capture_bag_f5a274d4`。数据为 mock，固件标识 `MOCK-ONLY`，不能作为机器狗数据集。测试已核对回放消费者收到与录制一致的数量及内容，包括请求输入、时长、单调期限与停止事件。

本机证据保存在 Git 忽略的 `.local/capture-validation/`：

- `final-check.log`：最终完整检查输出。
- `accepted-rosbag/`：bag、record/play 日志、QoS 和 SQLite 检查 JSON。
- `capture-independent-{ros,regressions,cli-transport}.xml`：独立检查的 JUnit 证据。
- `build/`、`install/`、`test-log/`：构建和测试产物。
- `source-sha256.txt`：本次通过检查的源码、测试与检查脚本清单及 SHA-256。

复现时在同等 Humble 环境安装 pySerial，并配置原版库与工具路径：

```bash
export DOGZILLA_VENDOR_SOURCE="$PWD/.scratch/system-audit-2026-11-05/image/usr/local/lib/python3.10/dist-packages/DOGZILLALib-3.1.9-py3.10.egg!DOGZILLALib.py"
export CAPTURE_BUILD_ROOT="$PWD/.local/capture-validation"
bash scripts/check-device-capture.sh
```

缺少原版库输入会跳过对应 PTY 测试，不能视为与本次无跳过验收等价。日志、bag 和审计快照为本机证据，本文不宣称它们已发布到团队共享位置。

## 真机验收与完整采集的剩余工作

- 机器人 arm64 构建、容器宿主 PID/权限与设备持有者检查、真实 UART 排他接管、退出后的设备释放。
- 只读有效反馈、持续采样间隔与负载、与雷达/相机共存；单位、轴向及实际样本时间继续核实。
- 现场逐段运动和停止观察，测量三档直行与左右转各一档；实际停止时序不能由 mock 结论替代。
- 磁盘扩容、校时、完整录制入口与持久目录、雷达退出异常处理、正式静止片段及全量录包/回放/无线取回验证。
- 数据集、说明书、缺失项与后续制造商核实。首批交付与全量覆盖核实仍按 spec 分别验收。

本轮未连接或操作机器狗，未更改分区、系统时间或厂商服务，未采集正式数据，未关闭 issue。

文档检查：本次新增文档及其引用目标存在，正式文档清单覆盖检查通过；`git diff --check` 通过。全索引检查另发现基线已存在的 `report/pstack-assessment-2026-11-06.md` 链接在当前分支缺少目标文件，已确认 HEAD 原有该引用，本次未改动这一无关报告条目。
