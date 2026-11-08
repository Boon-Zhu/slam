# ROS 首次采集入口独立实施检查

日期：2026-11-08。检查角色：独立检查子代理，未参与实现代码修改；主代理负责最终验收。本报告针对本轮工作区内容，不代表已提交版本或真机验收。

## 检查范围与结论

依据已确认的实现计划、[spec.md](spec.md)、[实机复核报告](../../docs/report/device-first-capture-verification-2026-11-08.md)、AGENTS.md 及阶段决议，检查 `dogzilla_capture_interfaces`、`dogzilla_device_capture`、`scripts/check-device-capture.sh` 和 `docs/development/device-capture-entry.md`。

本次审查提出的三项具体问题均已修复并复核。目前没有发现仍未修复、应阻塞这次软件实现验收的具体缺陷。此结论仅覆盖下述代码审查和隔离模拟验证，不等同于允许关闭 issue #4。

## 发现与闭环

### P1：退出时停止失败曾被隐藏，进程仍可能成功退出——已修复

原路径是节点先取消发布定时器，再关闭硬件工作线程。停止失败只进入内存事件队列；线程结束后 `controller.close()` 仍返回 true，节点既未持久输出这些事件，也未将停止失败反映为非零退出。

独立复现结果为：`close_result=True`、`state=CLOSED`、`last_error=stop_error: stop write failed`，队列含 `STOP_FAILED / FAULT / CLOSED`。因此“线程退出”曾被误当作“关闭成功”，操作者和数据集均可能失去最后一次停止失败的证据。

当前 `node.py:165` 的关闭路径根据 `controller.has_fault` 判断结果，向 stderr 输出 `shutdown_audit`；包含未发布事件、反馈原始字节及发布中的不确定批次，并明确 `not_confirmed_in_bag`。`node.py:231` 令失败返回非零。正常 SIGTERM 和注入停止失败的 SIGTERM 两种独立进程回归均通过；停止失败可在日志及退出码中观察。发布中的数据仅声明“未确认”，没有假装 DDS 发布成功就等同于 bag 已持久化。

### P1：写入结果不确定时曾未保留同地址响应归属——已修复

`SerialTrace.write()` 对底层写异常保留 `write_failed_unknown_count`，但查询失败后的未决地址判断原先只识别成功 `write`。当 MCU 已收到请求而主机写调用报错时，下次同地址查询可能错误接纳前次迟到响应。

当前 `vendor_adapter.py:398` 同时考虑 `write` 和 `write_failed_unknown_count`。独立注入“请求已交付，然后抛出 OSError”得到 `serial_error`、未决地址集合 `{1}`，原始 chunks 含 `write_request / write_failed_unknown_count`。不会直接重新发送该地址查询。

同时复读确认 `vendor_adapter.py:384` 将请求前 flush 中的旧帧与本次请求接收字节分开：旧帧不能解除本次失败请求产生的未决状态。设备占用检查按字符设备及 `st_rdev` 识别别名，避免仅按路径或权限位比较而漏检。

### P2：录包事件曾遗漏请求时长及计划停止期限——已修复

原 `REQUEST_ACCEPTED` 只有动作名，`MOTION_WRITTEN` 只有动作名及幅度。普通 topic rosbag 不保存服务请求，因而无法从数据集恢复请求持续时间、计算实际停止相对计划期限的偏差。

当前 `controller.py:151` 的接受事件包含 action、magnitude、duration_s；`controller.py:370` 的写入事件还包含 `motion_start_mono_ns` 和 `deadline_mono_ns`。计时起点仍在运动写调用成功后。独立核心回归验证写入延迟不会占用请求时长；实际 rosbag 读取和回放测试验证这些字段可以保留到消费者。

## 独立执行的验证

检查过程中代码仍由实施代理更新，以下是不同检查时点的执行记录，不将数量相加当作最终唯一测试数；最终冻结工作区的完整检查由主代理执行。

| 检查 | 独立结果 | 证据边界 |
| --- | --- | --- |
| adapter、controller、CLI 参数测试 | 64 passed | 包括指定原版 DOGZILLALib 文件、真实 pySerial、PTY 对端；没有机器人 |
| ROS 入口及 rosbag 往返 | 6 passed in 6.24s | 实际 rclpy 服务、受阻发布下 stop、metadata、关闭审计及 record→正常关闭→读取→play→订阅消费者 |
| 时长/期限修复、两种 SIGTERM、更新后的 bag 往返 | 4 passed in 6.00s | 新字段保留、真实进程退出码/日志、实际 bag 订阅内容核对 |

后两轮 JUnit 输出已从验证容器保存到仓库本地目录 `.local/capture-validation/capture-independent-ros.xml` 与 `.local/capture-validation/capture-independent-regressions.xml`，容器删除后仍保留。运行容器为 `slam-capture-validation`，加载 Humble 和本地接口 overlay，使用 mock/PTY；未连接或操作机器狗。

## 已检查的行为边界

- 串口及厂商对象由单硬件线程持有；查询可通过包装器中断，再由同一线程执行命令。没有另一个线程抢写 stop。
- 停止沿用原版库四次写入；部分写入或异常保留原始 chunks 和失败事件，不宣称真实停稳。写失败可导致 FAULT，而不是自动续跑旧动作。
- 单动作、明确幅度/时长、会话和请求去重；新会话不重放旧请求。ROS bag 回放只产生消息，不调用运动服务。
- 序列化反馈保留 raw bytes、厂商值、有效性和时间区间；额外关节字节及固件前缀没有被标准消息假设覆盖。
- 同地址查询未决状态跨进程保留；显式 fresh hardware session 仅是操作者声明，文档明确其不能由 SSH 重连替代。
- 发布与控制服务分离 callback group，实际测试阻塞发布时仍能提交并执行人工 stop。关闭不等待同步 DDS flush 才先处理停止。
- 停止期限使用单调时钟；拒绝 use_sim_time；系统时间变化以事件披露。观察时刻未冒充设备采样时刻。
- 文档区分 mock、软件写入、实际运动及正式全量数据集，包含持久日志、bag 收尾和异常边界；没有把临时入口写成完整 D→C→A 实现。

## 未验证项

未执行机器人 arm64 构建、真实容器 `/proc`/能力/设备持有者检查、真实 UART 排他接管、物理运动或停止、实际供电状态、持续采样频率及资源压力、与相机/雷达共存、磁盘扩容或首次正式全量录制。PTY 与 mock 不能证明这些结果。

本报告不替代最终全量格式/类型/build/test 检查，也不替代对厂商协议“每请求至多一响应、不主动推送/重复”的硬件假设核实。已有归属不明处理是软件保守行为，不是对未知硬件语义的证明。

## 最终增量检查：CLI 传输异常与 metadata

独立复读 `cli.py:83` 和 `cli.py:128` 的异常分支：`call_async`、等待响应、获取 future 结果以及等待执行事件发生异常后，返回 3 并报告带请求 ID 的未知结果；没有将这些异常错误归类成“未发送请求”，也没有重试、取消请求或发送额外 stop。服务确认拒绝仍返回 2，正常写入事件仍返回 0。此增量未发现具体缺陷。

独立执行新增 `test_cli_transport.py`：**4 passed in 0.18s**。四个故障点均检查只调用一次 `call_async`，未取消 future、未删除 pending request，且 stderr 含请求 ID 和未知结果说明。这里使用 mock 注入异常，仅验证客户端分类和副作用，不证明真实 DDS 断链时能观测机器人执行状态。JUnit 已保存为 `.local/capture-validation/capture-independent-cli-transport.xml`。

复读确认 `vendor_adapter.metadata()` 已提供 `backend=vendor`，与文档要求相符；`valid` 文档明确协议校验通过不等于物理单位或准确性验收。该增量不改变上述未验证项及主代理最终验收责任。
