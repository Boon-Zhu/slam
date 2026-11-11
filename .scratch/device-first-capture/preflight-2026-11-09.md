# 首次静止采集准备检查

检查日期：2026-11-09（Asia/Shanghai）。本轮按用户要求由子代理只读核查准备条件，主代理核实 issue、连接及执行顺序。初查后用户建立 SSH 复用会话；已完成实机存储检查，随后按用户“有读卡器，可以关机取卡”的回复正常关机。尚未扩容、校时或开始录制。

## 实机复核与备份准备更新

- `/dev/mmcblk0`：62,534,975,488 bytes；MBR label-id `0x738162de`。p1 起始 8192、大小 1048576 sectors；p2 起始 1056768、大小 62914560 sectors。卡尾空闲 58167296 sectors（27.736 GiB）。根 ext4 可用 5,425,496,064 bytes。
- 分区表保存在 `.local/device-first-capture-2026-11-09/preflight/partition-table.sfdisk`；文件系统、内核日志与服务快照保存在同目录 `device-state.txt`。分区表不是完整数据备份。
- 根文件系统仍挂载读写，ext4 有 `needs_recovery`；没有执行离线 fsck，不能以 mounted 状态的 clean 字段认定完整性验收通过。所取内核警告包含日志文件异常关闭记录。
- 电源诊断快照 `throttled=0x0`，温度 47.2°C；不据此替代现场稳定供电确认。OLED active/running/enabled；Docker 容器清单为空。
- 机器人仍报告 2026-11-04，`NTP=yes`、`NTPSynchronized=no`，本轮未校时。
- 用户确认尚无可恢复备份，且有读卡器、可以关机取卡。`sudo systemctl poweroff` 返回 0，随后独立 SSH 连接超时；这证明关机请求已受理及 SSH 不再可达，物理停机/断电仍由现场观察。
- 已提示用户等系统停止活动、断开电源后取卡；Windows 格式化/修复提示需取消。
- 电脑插卡前 Windows 磁盘基线：Disk 0 Samsung NVMe（系统盘）；Disk 1 SanDisk NVMe（数据盘）。两者均非目标 SD 卡。插入后必须结合新增设备、62,534,975,488 bytes 容量和分区布局再次定位，不能假定固定磁盘号。
- 下一步为离线整卡备份至电脑、核对镜像长度/哈希及可读性，再安排扩容；尚未创建完整镜像或声明备份可恢复。

### Windows 离线备份进行中

- 用户已把卡插入读卡器并确认 Windows F:。实测 F: 对应 Disk 2，USB `MXT-USB Storage Device`，序列号 `150101v01`，总容量 62,534,975,488 bytes。两个分区 offset/size 与机器人分区表一致，非系统盘。F: 本身只是 512 MiB FAT32 启动分区，不能只复制 F: 文件作为整机备份。
- 目标 `E:\robot-backups\dogzilla-20261109-before-expand\card.img`；检查时 E: 可用 227,165,216,768 bytes。
- 本地脚本 `.local/device-first-capture-2026-11-09/backup/backup-sd.ps1` 经子代理静态审查。Windows UAC 提升后，验证磁盘身份及原始 MBR，持有 F: 的 FSCTL_LOCK_VOLUME；源 PhysicalDrive2 仅 GENERIC_READ，目标 CreateNew。复制完整卡并计算源读取流 SHA-256，完成后独立重读目标计算 SHA-256，匹配才重命名 `.partial` 为 `.img`。
- 第一次运行在读取循环前遇到 PowerShell Math.Min overload 的 Int32 溢出，0 字节临时镜像及日志保存于 `attempt-1/`。修复为显式 Int64 后，在 Windows PowerShell 内存验证 7455 次分块合计 62,534,975,488 bytes（末块 6,291,456 bytes）；第二次运行已开始复制。源卡没有原始写入操作。
- 状态写入目标目录 `status.json`；检查时约 18 MB/s，预计复制约 55 分钟。此处只记录进行中，完成与验收结果须另行追加。
- 完成后使用 `verify-image.sh` 将镜像的根分区映射为只读 loop，执行 `e2fsck -f -n` 并读取系统信息；该步骤尚未执行。不自动修复镜像、不改源卡。
- 卷锁机制依据 [Microsoft FSCTL_LOCK_VOLUME 文档](https://learn.microsoft.com/en-us/windows/win32/api/winioctl/ni-winioctl-fsctl_lock_volume)：锁定前刷新缓存，锁持有期间阻止其他文件访问；关闭句柄释放锁。

### 备份中断：源设备读取失败

- 用户指定 GPT-6.1 Terra 子代理监控，主代理每 10 分钟检查。第二次备份在 2026-11-09 21:41:00（Asia/Shanghai）失败，源 `FileStream.Read` 报 `System.IO.IOException: 指定不存在的设备`；主代理收到子代理即时通知后停止等待并调查。
- 留存 `card.img.partial` 为 32,438,747,136 bytes（约 30.21 GiB），尚未生成完整镜像或校验回执。状态文件的 `bytes=0` 是异常报告逻辑重置，不能据此认定临时文件为空；实际长度已另查。
- 备份进程与临时防睡眠进程均已结束。随后 Windows 仍列出 Disk 2、F:，容量及序列号一致；当前在线不能否定先前读取失败。
- 经 UAC 执行只读 `probe-sd.ps1`：原始 MBR 身份匹配，在 0、32430358528、32438747136、32753254912、62533926912 五个偏移各读 1 MiB 均成功，包含中断边界与卡尾。结果保存在目标目录 `read-probe-20261109T134310.json`。这仅是短读恢复证据，不能替代完整连续读取，也不能确定故障根因。
- 针对存储/USB provider 的 Windows System 事件查询未得到条目；不声称已排除设备掉线。已询问用户是否经过集线器/扩展坞，以及是否发生拔插/松动。
- 当前没有有效完整备份，暂不扩容；保留临时镜像和失败证据，待连接情况明确后重试。

### 用户确认接触不良可能性并要求重试

- 用户表示刚才可能触碰读卡器导致接触不良，明确要求重试，并授权删除无用的旧镜像。此为现场解释，未通过系统事件独立确认根因。
- 重试前再次核实 Disk 2/F: 的容量、USB 序列号及分区布局一致，旧备份和防睡眠进程已结束。
- 已将第二次失败的 status/source/MBR/脚本/短读结果保存在 `attempt-2/`，并按用户授权删除 32,438,747,136 bytes 的未完成镜像及 `attempt-1/` 的零字节镜像；删除记录为 `attempt-2/cleanup.json`。
- 现有未完成镜像没有最终源流哈希，重试从头开始，不将旧数据未经校验拼接为完整镜像。第三次备份继续执行只读源盘、卷锁、完整长度及源流/目标读回 SHA-256 检查。
- 小修复：异常 status 保留本轮已复制字节数，避免再次显示 0；防睡眠脚本改为显式传本轮进程 ID，避免复用旧 PID。

## 当日收尾：用户要求明天继续

- 第三次复制 PID 36720 顺利越过先前接触中断位置，但在最后 6 MiB 处报 I/O 错误，已复制 62,528,684,032 bytes。此次是脚本卡尾缓冲问题：.NET Framework FileStream 在请求量 6 MiB 小于内部缓冲 8 MiB 时，实际预读 8 MiB，超过设备末端 2 MiB。依据为精确失败位置、[微软实现](https://github.com/microsoft/referencesource/blob/main/mscorlib/system/io/filestream.cs#L1400-L1411)及最小对照读取；不将此次等同于再次接触不良。
- 源 FileStream 内部缓冲已修为 512 bytes，外部数组/常规块仍为 8 MiB。`read-tail.ps1` 连续读取末尾 6 MiB 两次，用时 735 ms，两次源哈希与保存文件哈希均为 `b69dae56a14d1a8314ed40664c4033ea0a550eea2673e04df42a66ac6b9faf2c`。结果 `tail-read.json`，尾文件 `card-tail.bin`。
- 第三次失败记录保存在 `attempt-3/`。只将验证过的 6 MiB 追加到原 partial，已达到整卡精确长度 **62,534,975,488 bytes**；追加证据为 `tail-append.json`。
- 原复制进程的完整源 SHA 状态已丢失，不能从补齐后的镜像自身哈希伪造源比对证据。准备 `verify-sd.ps1`：再次复核身份/锁 F:，用修复后的精确长度循环只读整卡计算 SHA，再独立读取镜像比对；成功后才改名 `card.img` 和生成 `verification.json`。不能对 raw source 使用读到 EOF 的 ComputeHash，否则会多发一次越界读取。
- 校验 PID 15232 启动后，用户明确要求“今天先做到这里，剩下的明天再处理”。已执行停止；Windows CIM 最终核实校验、停止辅助及此前防睡眠 PID 均不存在。镜像和日志保留；`status.json` 已改为 `paused_by_user`，`verification-paused-state.json` 保留停止前进度，`stop-report.json` 记录已确认退出。没有让校验留在后台过夜。
- 当前文件：`E:\robot-backups\dogzilla-20261109-before-expand\card.img.partial`，58.240 GiB，长度已补齐，**完整源/镜像哈希比对和 ext4 检查均未完成**。尚无 `card.img` 或成功 `verification.json`，不能报告备份验收通过。
- 机器人仍关机、SD 卡在电脑读卡器中；磁盘分区与文件系统尚未扩容，未校时、未静止录制。

### 明天继续顺序

1. 用户重新确认卡已连接并固定；重新核对 Windows 盘号/盘符、容量、序列号、分区及 MBR，不能只凭历史 Disk 2/F: 执行。恢复前保存旧校验日志；若设备编号变化，修正实际脚本并重新核对。
2. 经 UAC 运行已修正的 `verify-sd.ps1`，只读整卡哈希与现有完整长度 partial 比对，不需要再次复制或删除镜像。约 55 分钟；仍可由 GPT-6.1 Terra 每分钟监控、主代理约每 10 分钟查看。重新启动防睡眠脚本时显式使用新 PID。
3. 成功后 `verify-image.sh` 以只读 loop 检查镜像 MBR、FAT32 标记、ext4 UUID，执行 `e2fsck -f -n` 并读取系统信息。不会修复源卡或镜像；完成后释放 loop。报告未做硬件恢复测试的边界。
4. 备份验收通过后，再安排安全弹出、装回机器人、供电及扩容。原厂 APP/OLED 开机配置仍 enabled，重新上电可能运行厂商程序，需现场准备；不要把上电当作没有动作副作用的操作。
5. 扩容和容量验证后，继续真实校时、部署、资源交接及首轮静止录制。没有授权推送、发布或关闭 issue。

## 已核实

- 当前代码 HEAD：`4d137a41f01379f3197dba80720405366e846893`，检查时工作树干净。
- GitHub `Boon-Zhu/slam` issue #4 为 open，标题“A：核实设备数据并完成首次全量采集方案”，没有评论。要求保留全部实际可获取数据，输出覆盖/缺失清单、采集/回放步骤及证据；没有发布更新或关闭 issue。
- GitHub 账号核实成功。代理请求 EOF，命令级清空代理变量后 REST 读取成功，没有修改永久网络设置。
- 机器人 `192.168.8.88:22` 响应，严格主机密钥校验未报错；BatchMode SSH 认证失败，旧 `/tmp/slam-readonly-20261109.sock` 不存在。因此当前设备状态尚未核实。
- 电脑 Windows E: 可用约 212 GiB；WSL 文件系统报告约 574 GiB，备份预算不能按后者计算。完整卡备份容量还须根据当前机器人卡容量重新核算。

## 前置条件与执行顺序

1. 恢复 SSH 认证会话；确认现场机器狗静止、稳定供电、有人观察。当前只计划静止轮，运动保持禁用。
2. 只读取得 `lsblk`、根挂载来源、`sfdisk --dump`、分区空闲区、ext4 信息、剩余空间、内核存储错误及现有备份位置。历史“30 GiB 根分区＋27.736 GiB 卡尾空闲”仅是 11-08 快照。
3. 明确可恢复备份及恢复方式。保存分区表不能替代系统/数据备份；在线复制活跃根文件系统也不能直接声称为一致可恢复镜像。需要离线备份时先完成关机/介质操作安排。
4. 当前布局及备份条件确认后，制定针对实际 p2 的扩容操作：保持起始 sector、类型与标识不变，仅延伸末端；再扩 ext4。执行前保存原始布局，执行后核对分区表、内核所见容量、文件系统容量、挂载和剩余空间。内核不能更新分区大小时停止后续步骤，单独处理重启条件。尚未生成或执行修改分区的命令。
5. 在机器人 arm64 新目录构建本轮两个包，保留之前只读验证工作区。使用宿主数据 bind mount，全部预期设备映射，宿主 PID 视图及 `SYS_PTRACE`/`DAC_READ_SEARCH`；运行容器实际 ID 生成镜像证据。
6. 核实宿主时钟同步服务和可信时间源。模板的 chrony 适配器需要真实 `chronyc`/daemon socket，不能假定已安装；配置实测偏差预算及有效验证输出。
7. 核实 usb_cam 实际版本、executable、支持格式、分辨率/帧率、配置和时间语义；核实 MS200 启动及退出。确定实际设备路径、来源、容量预算、超时和静止轮时长。
8. 核实 APP TCP 6000、完整进程、OLED 状态及设备持有者。需要临时停用时先按已查明对象落实当前会话授权；保留开机配置，不自动恢复。按字符设备 `st_rdev` 扫描宿主 `/proc/*/fd`，权限缺失不能视为无占用。
9. 填写实际 vendor 配置，预检电脑 Humble 环境 SSH/SCP 导出通路，再运行 stationary `prepare → start → status → finish`。默认 `enable_motion=false`；缺失来源须明确接受，不能自动降级。
10. 正常关闭 bag，检查 SQLite、数量、覆盖、日志、shutdown_audit、设备释放；无线导出、哈希核对和实际隔离回放。导出原件保留，不自动 clean。上述通过后才认定静止流程验收通过。

## 已识别的具体配置缺口

- `src/dogzilla_device_capture/config/round_vendor.json`：入口/相机 YAML、镜像 ID 占位，`expected_files` 为空，`max_offset_s` 为 null；容量及超时只是示例。
- `docs/development/device-capture-entry.md` 的旧容器示例只映射 UART0、没有持久数据目录，不能原样用于全量采集。
- `archive.py` 的远程导出使用 `ssh/scp -o BatchMode=yes`，不直接支持额外 SSH 参数；必须在实际运行归档工具的电脑容器内验证受控连接适配，避免结束后才发现无法导出。
- 初查时尚无机器人新证据；后续布局、时钟及服务快照见本页更新。相机、完整设备占用、运行负载和完整备份仍未验证。

依据：[入口指南](../../docs/development/device-capture-entry.md)、[轮次指南](../../docs/development/device-capture-round.md)、[已确认方案](spec.md)、[issue #4](https://github.com/Boon-Zhu/slam/issues/4)。

## 2026-11-10 执行更新

用户恢复 SSH 并确认镜像可恢复、供电稳定后，已完成 p2/ext4 在线扩容至 57.7363 GiB。另经明确授权完成 APP/OLED 及媒体服务临时交接。首次真实联合静止轮次 `20261110T162513-9b883385a677` 已录制、封存、无线导出及实际回放；但存在原始图像缺帧、收录停顿和驱动退出异常，静止验收未通过，未进入运动轮次。正式结果见[实测报告](../../docs/report/device-first-stationary-capture-2026-11-10.md)。上面的“尚未执行”均保留为 11-09 准备检查当时的状态。
