# 采集脚本审查问题修复

日期：2026-11-09。承接[首次软件验收](device-capture-round-acceptance-2026-11-09.md)后的独立代码审查。用户要求修复两项 P1、两项 P2，P3 暂缓并记录。只修改项目自研代码、回归测试和说明；未连接机器人、操作真实服务、校时、运动或清理既有采集数据，未提交或推送。

## P1/P2 修复

| 问题 | 修复与回归覆盖 |
| --- | --- |
| P1：旧 clean 核验后可删除新 current | clean 在生命周期锁和 supervisor 锁内读取状态、核对回执与原件哈希、删除；seal-orphan 同样在锁内检查。受控并发测试暂停哈希检查，确认另一 clean 与 prepare 均被锁拒绝；新轮建立后旧回执不能删除新轮。 |
| P1：校验失败后旧成功回执仍有效 | 验证开始先撤销旧回执，再写不可清理状态；只有整次检查成功才重新生成成功回执。覆盖内容损坏、文件缺失/增加、manifest 无法解析、回执写盘失败，以及修复副本后重新验证成功才可清理。 |
| P2：新探查失败复用旧 READY | 每次 probe 使用独立请求路径和日志，命令失败直接失败，不读旧文件。覆盖 start/finish 超时保留旧证据但不执行，以及新请求未生成报告时拒绝复用上次结果。 |
| P2：leader 退出后遗漏子进程 | 根据 /proc 的进程组检查所有活跃成员，分阶段 SIGINT/SIGTERM/SIGKILL；即使 leader 已退出也等待整组结束。无法核实时尝试其他驱动收尾但不封存；seal-orphan 同样拒绝遗留进程组。真实临时 fork 测试覆盖 leader 先退出、leader 收到信号才退出、后代忽略 SIGINT/SIGTERM，核对最终无活跃成员且封存日志哈希稳定。 |

以上依据 spec Q39 的导出校验与显式清理、Q41 的当前入口门禁、Q37 的完整收尾要求。回执是校验时刻的文件凭据；这次修复撤销的是电脑当前规范回执，不具备跨机撤销任意旧文件副本的能力。操作时应使用最后一次验证后的回执，失败后不能沿用已传输的旧成功文件。

## 验证

使用本地 `slam-humble-desktop:local`，Ubuntu 22.04 / Humble / Python 3.10.12；容器无网络、无物理设备，仅共享工作区，ROS 进程通过本容器 loopback 通信。pySerial 3.5 由已有 wheel 安装到临时容器目录，使用原样厂商库审计副本进行 PTY 回归，不修改系统或上游。

完整检查入口为 `bash scripts/check-capture-round.sh`。本次包装脚本、构建、日志和新合成录包独立保存于 `.local/capture-round-review-fixes/`；与首次验收目录分开。

完整检查通过：

- Ruff lint/format 通过；strict mypy 通过，检查 16 个运行源码文件。
- 两包 colcon build 通过。
- 直接 pytest：136 passed，70.08 秒；包含新增 9 项测试，以及强化的三种副本损坏回归断言，无跳过。
- colcon test/test-result：136 tests，0 errors，0 failures，0 skipped。
- 正常录制→关闭→导出→实际 ROS 回放→显式清理，以及来源缺失/录包失败保留原件的合成端到端测试均通过。

日志：`.local/capture-round-review-fixes/check-20261109T124029Z-52.log`；colcon JUnit：同目录下 `build/dogzilla_device_capture/pytest.xml`；新端到端产物：同目录下 `e2e/`。`git diff --check` 通过，新文档引用目标存在。文档索引中原有的 `pstack-assessment-2026-11-06.md` 链接目标缺失，本次未改动这一无关事项。

本地测试不替代 arm64、真实驱动联调或物理停稳验证。

## P3 暂缓

- **状态：暂缓修复（用户明确决定，2026-11-09）。**
- **事项：Possible Duplicated Code。** `round_config.write_json`、`recording.atomic_json`、`archive._write_json` 各自实现临时 JSON 写入和替换，父目录创建、NaN 校验及 fsync 策略存在差异。
- **影响：** 后续调整证据持久化规则时需分别维护三处；这是设计建议，没有确认为硬规范违规。
- **本轮处理：** 保留三套实现，不进行统一抽取。P1 所需的回执失效处理使用现有写入方法，不代表已解决此 P3。
- **后续处理：** 再次授权统一持久化逻辑时，先确认各调用方的语义和错误处理，再抽取共享实现并验证相关故障路径。
