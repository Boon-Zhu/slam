# 快速验证版 Cartographer 2D 建图方案

确认日期：2026-11-25。方案选择已确认，部署与接口能力按下列证据范围分别验收。

## 已确认决策

**已确认快速验证版采用未修改的 Cartographer 2D，单 LaserScan、无外部 odom/IMU，开启 `TRAJECTORY_BUILDER_2D.use_online_correlative_scan_matching=true`。** RF2O + slam_toolbox 保留为后续出现需要时的备选，不再与 Cartographer 并列为当前未定选型；本轮没有运行或判定其优劣。

用户本轮亲自检查当前方案产出的地图，确认与采集场地环境轮廓吻合，现场转向观察印象支持 **+17.0°／−53.7°**，并明确授权落盘当前算法方案。这是本数据/场地的人工定性复核与方案确认，不是校准轨迹真值或厘米级精度测试，也不代替Pi部署、低速连续现场建图与实际停车验收。此前“仅候选、尚未选定”的描述保留为历史，由本节更新。

### 第一阶段实际完成

- [x] 两轮输入完整性：静止168个、动态169个manifest文件全匹配，SQLite完整；分别1220/5647扫描。
- [x] 固定实际版本、依赖、配置、TF、回放时钟，原始包只读，禁网隔离运行；无恒等odom或控制指令积分。
- [x] 静止1×、动态基线1×、动态基线5×、改进配置动态5×四轮完成扫描→建图→结束→正常退出最终优化→pbstream→同源PGM/YAML→新进程同版本读取。
- [x] 基线转向异常已作输入、时间/TF、资源、配置分析及同速对照：基线1×/5×的最终pbstream和PGM哈希相同；仅开启相关匹配后左/右转从+5.60°/−5.72°改善至+17.00°/−53.68°。独立扫描轮廓诊断约+17°/−54°，两组窗口一致、四个等待负控0°。
- [x] 三段直行括窗估计约0.340/0.651/0.334m；分析覆盖五动作与六等待窗。括窗含相邻保留节点的少量额外等待，不能当作精确运动起止真值；节点数不是扫描接受/丢弃计数。
- [x] 用户完成场地轮廓及转向量级人工复核，确认采用当前改进配置。
- [x] 保存及B/D接口缺口明确拆至 [保存研究 #7](https://github.com/Boon-Zhu/slam/issues/7)、契约草案 [契约草案 #16](https://github.com/Boon-Zhu/slam/issues/16)、自研实现 [自研保存层 #17](https://github.com/Boon-Zhu/slam/issues/17)。
- [ ] 改进配置独立1×回放与目标Pi5/Humble/arm64安装、CPU/RSS/温度/处理积压/保存延迟。
- [ ] 外参标定/时间语义与自动运行故障报告确认；内部逐帧scan接受/拒绝统计尚未完整测量。
- [ ] B/C/D接口确认及A/C执行能力、低速连续场地建图、失败停车与人工确认、真实闭环验收。

#6 状态保持 **OPEN / needs-info**，原因是上述部署与集成证据尚缺；**不再表示算法选型未定**。M2尚未完成。

### 固定来源与配置

| 项目 | 已验证版本 |
| --- | --- |
| 环境 | Ubuntu22.04 / ROS2 Humble / Python3.10 / x86_64离线容器；非Pi验收 |
| core包 | `2.0.9004-1jammy.20260226.010834` |
| ROS包 | `2.0.9002-1jammy.20261110.122816` |
| core源码 | `ros2/cartographer` tag2.0.9004，commit `1489fc933b6e0b1da936ca08af462abe559dd02e` |
| ROS源码 | `ros2/cartographer_ros` tag2.0.9002，commit `43cd92bc8c4bf1a90f50eddbbbd724a899ceebe1` |
| 本机镜像 | `slam-cartographer-validation:20261125`，`sha256:1d989115001acfb296ebae8f89b4f1d8bba9f495e551aff1f2c4e12f788f8367` |
| 已确认工作Lua | `cartographer_scan_only_correlative.lua`，SHA256 `335772443e753f1c7adf89cab18eec25968f77416a32506f4529427d5fcf9546`；只在实验后修正了准备期注释，实际运行字节另存快照 |

输入轮次：静止`20261111T110119-67933b8eeecf`；动态`20261111T162132-97e6f5fe7058`。A负责`base_link→laser_frame`（当前用厂商z=0.18m/单位旋转，未标定），B负责`map→odom→base_link`，D确保每段唯一发布者。离线算法用统一use_sim_time、唯一bag clock；运行前准备消费者和静态TF，不使用触发起播clock回退的delay。真机时钟按共同基线配置，不直接照搬sim_time。

原生交付 `.pbstream`，可查看地图由同一最终pbstream导出PGM/YAML。正常退出最终化路径已验证，但在线finish/write无最终优化屏障，完整可重试保存层由 [自研保存层 #17](https://github.com/Boon-Zhu/slam/issues/17) 实现。算法确认不自动批准依赖升级或修改上游。

### 已确认自有Lua全文

下列include使用上述固定包的原版默认配置，不修改上游。完整依赖/默认配置快照已本地保留；Dockerfile的可变tag/apt配方不是未来重建锁，本地精确复验使用已记录镜像ID。

```lua
-- Offline-tested on 2026-11-25; see report.md for scope and limits.
-- Original executed bytes are retained in each run/configuration_snapshot/.
-- Keep upstream map_builder.lua and trajectory_builder.lua unmodified.
include "map_builder.lua"
include "trajectory_builder.lua"
options = {
  map_builder = MAP_BUILDER,
  trajectory_builder = TRAJECTORY_BUILDER,
  map_frame = "map",
  tracking_frame = "base_link",
  published_frame = "base_link",
  odom_frame = "odom",
  provide_odom_frame = true,
  publish_frame_projected_to_2d = true,
  use_pose_extrapolator = true,
  use_odometry = false,
  use_nav_sat = false,
  use_landmarks = false,
  num_laser_scans = 1,
  num_multi_echo_laser_scans = 0,
  num_subdivisions_per_laser_scan = 1,
  num_point_clouds = 0,
  lookup_transform_timeout_sec = 0.2,
  submap_publish_period_sec = 0.3,
  pose_publish_period_sec = 0.005,
  trajectory_publish_period_sec = 0.03,
  rangefinder_sampling_ratio = 1.,
  odometry_sampling_ratio = 1.,
  fixed_frame_pose_sampling_ratio = 1.,
  imu_sampling_ratio = 1.,
  landmarks_sampling_ratio = 1.,
}
MAP_BUILDER.use_trajectory_builder_2d = true
TRAJECTORY_BUILDER_2D.use_imu_data = false
-- Bounds copied from the actual LaserScan message, not inferred sensor calibration.
TRAJECTORY_BUILDER_2D.min_range = 0.05
TRAJECTORY_BUILDER_2D.max_range = 20.
TRAJECTORY_BUILDER_2D.use_online_correlative_scan_matching = true
return options
```

### 成果与证据位置

本机 `.scratch/mapping-validation-2026-11-25/`：总README、candidate/report.md、candidate/run_comparison.json、contract/scan-rotation-findings.md；完整包清单candidate/candidate-packages.tsv、实际配置快照及checks日志。

采用配置的成果在`candidate/dynamic-correlative/`：final.pbstream SHA256 `cf35ffec604aaea8c246b86107af387615d50a0b68092ee071b3bbb3e006ec4d`；map.pgm SHA256 `9874322c4bdacb133155768b34fb3d6807347d6302b604b0d920154b526feba2`，155×81、0.05m；另有map.yaml/map.png及重读日志。该目录与镜像目前仅本机保留，没有上传二进制产物。

方案已落盘至本地`docs/architecture/cartographer-mapping.md`，正文关键决策与完整参数同时在 #6 展开，团队无需访问本机路径即可评审；本轮未提交/推送仓库文件。

共享记录：[算法方案与后续验证 #6](https://github.com/Boon-Zhu/slam/issues/6)。本文件记录算法与配置决策；正式launch、ROS package与B入口随后续实现封装，实验入口不直接提升为正式接口。
