# 分步采集工具本地验收

检查日期：2026-11-09。基线分支 `feature/device-capture-entry`，起点 `a036139`。本报告只覆盖本轮软件实现和本地 Humble 合成数据验证；没有连接机器人、停止真实服务、校时、扩容、真机运动或正式采集。按用户要求，本轮由实施代理实现和集成，独立代码审查留到下一轮；本报告不是代码审查结论。未提交、推送或关闭 issue。

后续已完成独立代码审查，发现的 P1/P2 修复及 P3 暂缓决定另见[审查问题修复记录](device-capture-round-review-fixes-2026-11-09.md)；下文保留首次验收的原始范围和结果。

## 实施范围

依据首次采集 spec Q27–Q44，新增 `capture-round prepare/start/status/finish/abort/seal-orphan/clean`，配合独立 `round_handoff` 和 `capture-round-archive export/verify/replay`。使用步骤见[分步采集指南](../development/device-capture-round.md)。

- prepare 的时钟、部署、存储/所有权、启动和来源检查顺序已实现；current 存在即拒绝重新 prepare，不改时或覆盖。真实配置与 synthetic 明确分开，未填真实校时偏差、镜像、哈希或驱动配置时失败。
- recorder 自身通过 ROS 订阅与原版 rosbag2 writer 写入数据。实际匹配和已写入消息证据决定 start 成功；静止事件话题可以零消息，不伪造事件。
- 单来源中断保留其他记录，整体录包失败调用现有 stop 一次；pending/active 动作拒绝正常 finish。关闭包检查后停止驱动/入口，保存 shutdown_audit 和资源核对；不自动恢复厂商程序。
- 每轮机器人固定 current，电脑按唯一 ID 独立导出。完整文件清单/哈希、导出来源回执和显式 clean 分离；异常轮次也保留并导出。
- 实际外部配置/代码按 expected_files 保存内容快照及映射；导出附实际自定义消息定义、构建文件、代码和操作指南。

新增运行模块为 `round_config.py`、`round_preflight.py`、`round_session.py`、`round_handoff.py`、`recording.py`、`archive.py`、`synthetic_sources.py`；新增两份配置、五份测试和 `scripts/check-capture-round.sh`。原串口控制器/厂商适配器和上游代码未修改；两个包的安装/依赖声明增加新入口、运行依赖、指南和接口构建文件。

## 环境与检查

使用已有本地 `slam-humble-desktop:local`，Python 3.10.12、Ruff 0.17.4、mypy 2.4.1、pytest 8.4.2。容器采用默认隔离 network/IPC、`ROS_LOCALHOST_ONLY=1`；没有接入物理设备。全部测试设 `PYTHONDONTWRITEBYTECODE=1`。

原版库 PTY 回归使用仓库既有审计副本 `DOGZILLALib.py`（SHA-256 `3d05141c71b1066e2274cb0d842bd45b328c6d57a9032b7484494433b185585d`）。pySerial 3.5 从已有 `.local/capture-validation/wheels/` wheel 安装至一次性容器 `/tmp/capture-round-deps`，仅通过本次 PYTHONPATH 可见，不修改宿主、镜像或上游。

实际执行入口及证据：

| 检查 | 结果/证据 |
| --- | --- |
| Ruff lint/format、strict mypy | 通过，16 个运行源码文件；`.local/capture-round-check/final-acceptance.log` |
| 两包 colcon build/test/test-result | 127 tests，0 errors，0 failures，0 skipped；`check-20261109T121512Z-1.log` 和 `build/dogzilla_device_capture/pytest.xml` |
| 稳定文件上的直接 pytest | 127 passed，0失败/跳过，63.20s；`.local/capture-round-check/final-pytest.log` 与 `final-pytest.xml` |
| 配置快照及最终正常/异常轮次受影响检查 | 15 passed；`final-acceptance.log`、`final-affected.xml` |
| 导出内自定义接口独立构建 | 1 package finished，3.00s；`.local/capture-round-check/export-interface-log/`，最终结果见 `final-pytest.log` |
| 源码/测试/配置指纹 | `.local/capture-round-check/source-sha256.txt` |

完整检查命令为 `bash scripts/check-capture-round.sh`；它复用既有入口检查并包含新增测试。复现前按入口指南加载 Humble/overlay、设置 `DOGZILLA_VENDOR_SOURCE` 和 pySerial 路径。最终受影响命令为 `pytest test_round_session.py test_round_e2e.py`；最终全套直接测试使用 `pytest src/dogzilla_device_capture/test -q --junitxml=.../final-pytest.xml`。日志均在 Git 忽略的 `.local/`，不宣称已发布给团队。

## 可复查端到端产物

**正常轮次**：`.local/capture-round-check/final-e2e/normal-d384faf3/`。

- `e2e_result.json` 为实际 prepare → start → 独立 CLI status 重连 → finish → export → verify → ROS replay → 显式 clean 的成功结果。
- 电脑副本：`computer/20261109T121807-d544ee155b8e/`，140 个 manifest 文件；机器人 current 已显式清理，电脑副本保留。
- 实际回放：feedback 71、status 22、metadata 1、scan 10、image 10、parameter_events 1，events/rosout 为 0。8 个话题的数量及完整序列化内容（包括嵌入时间戳）均一致。
- 0 事件是本次静止合成轮次的真实结果，不被填充为动作证据。bag 关闭后的 SQLite、metadata、覆盖检查与电脑哈希/回放分别保存。

**异常轮次**：`.local/capture-round-check/final-e2e/failure-76e74ed2/`。

- 缺少 image 默认拒绝 start，显式接受 `/camera/image_raw` 后才开始；使用明确 `motion` 的 mock 入口。
- 人工测试命令触发 mock 动作，动作未结束时 finish 被拒绝。测试随后 SIGKILL recorder，supervisor 调用现有 stop，回执 returncode=0；该结果仅证明软件停止调用与事件，不证明物理停稳。
- 最终 `finished_with_errors`；残留包缺失正常关闭 metadata，如实记录文件检查失败，未自动恢复或覆盖。
- 导出副本 `computer/20261109T121821-a729d87cc839/`，141 个 manifest 文件，哈希通过。机器人原件仍在 current；异常 bag 不宣称通过实际回放。

主代理随后只核对产物，未做代码审查：正常副本140文件哈希一致、SQLite integrity ok/115条、8话题回放一致且current已清理；异常副本141文件哈希一致、stop rc0、原件保留。证据为 `.local/capture-round-check/root-brief-acceptance.json`。

附加测试覆盖实际 writer 写失败不虚增计数、来源中断/恢复区间、handoff失败/超时保留日志与并发拒绝、错误回执/文件篡改/禁止覆盖、后台未知、残留进程阻止封存、校时未同步、固件准入与外部配置内容快照。

## 实施中发现与限制

本机 host network+host IPC 模式曾出现 DDS graph 可见但消息不到；改为所有进程位于同一隔离容器后实际 DDS/录包测试通过。原因尚未确认，没有修改生产代码掩盖接收失败，也不能据此推定机器人存在相同问题。初次套件另暴露两个测试假设：播放器自生系统事件不保证必达；禁止运动的静止入口也拒绝 stop。测试分别改为核对录包内容、显式 motion mock 故障场景，保留真实失败语义。

真机仍需核实实际 chrony/其他时间源及权限、host PID/proc 权限、入口部署和资源释放、MS200 联合录制/退出、usb_cam实际版本与参数/帧时间、相机/雷达/反馈并行负载与存储增长、真实丢帧/中断、Wi-Fi SSH/SCP 导出、实际运动和停稳。模板的相机与校时缺省项刻意不能通过准入；本轮未取得新的驱动硬件能力证据。没有以静止报告作为运动门禁，没有修改六轮共识或全量覆盖/issue #4 的完成条件。
