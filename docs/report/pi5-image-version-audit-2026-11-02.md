# 树莓派 5 与厂商 Humble 镜像版本核实

检查日期：2026-11-02。来源：用户提供的拆机开发板，经 SSH 实际读取宿主信息及本地 Docker 镜像内容。未安装升级软件，未运行厂商启动脚本或机器人节点，未访问串口或启动运动。

## 宿主与镜像身份

| 项目 | 实际结果 |
| --- | --- |
| 开发板 | Raspberry Pi 5 Model B Rev 1.1 |
| 宿主系统 | Debian GNU/Linux 12（bookworm），aarch64 / arm64 |
| 宿主内核 | 6.6.54-v8-16k+ |
| 宿主 Python | 3.11.2 |
| 宿主 ROS 可见性 | `/opt/ros` 不存在，当前登录环境 `command -v ros2` 无结果 |
| 厂商版本文件 | `/home/pi/Version.txt`：`Card NO.64, Version:2.0.0, Released 20250619` |
| 厂商启动入口 | `/home/pi/run_humble.sh` 指向 `yahboomtechnology/ros-humble:3.8` |
| 本次核实镜像 | `yahboomtechnology/ros-humble:3.8`，linux/arm64 |
| 镜像 ID | `sha256:7e79c61b64b81311caf297640e5c6fd70279be4cbd38c2c087e8e3395e566047` |
| RepoDigests | 空；未获得可用于远端拉取复现的仓库 digest，镜像 ID 仅标识本次本地内容 |
| 其他本地 tag | 同仓库 3.5、3.6、3.7；未逐一检查内部版本 |

宿主启动脚本使用 privileged、host 网络并挂载设备；本轮仅阅读，未执行。镜像的 Entrypoint 和 Volumes 均为空，Cmd 为 `/bin/bash`。镜像内 `/root/.bashrc` 引用 `/opt/ros/humble/setup.bash` 与 `~/yahboomcar_ws/install/setup.bash`，本轮未执行这些 shell 初始化文件。

## 镜像内部版本

| 项目 | 实际结果 |
| --- | --- |
| 系统 | Ubuntu 22.04.4 LTS（Jammy） |
| Python | 3.10.12 |
| ROS 发行版目录 | `/opt/ros/humble` |
| ros-humble-ros-core | 0.10.0-1jammy.20240220.155811 |
| ros-humble-rclpy | 3.3.12-1jammy.20240219.073613 |
| ros-humble-rclcpp | 16.0.8-1jammy.20240219.080509 |
| GCC / G++ | 11.4.0 / 11.4.0 |
| CMake | 3.22.1 |
| colcon-core | 0.16.0 |
| DOGZILLALib | 3.1.9 |
| NumPy / pyserial | 1.21.5 / 3.5 |
| setuptools / pip | 59.6.0 / 22.0.2 |
| pytest | 6.2.5 |
| mypy / Ruff | 当前 Python 环境未找到安装元数据 |

ROS 包版本来自 `dpkg-query`，Python 包版本来自标准库 `importlib.metadata`。没有导入或实例化厂商控制库。已有 pytest 版本是厂商环境事实，不等于本项目 CI 必须采用的版本。

后续决议更新：Ruff、mypy、pytest 工具组合已确定，具体版本与兼容性仍待开发/CI 试运行，见[阶段决议 §7.22](../architecture/interface-baseline-decisions.md#722-已确认开发板环境对照与-python-检查工具组合)。本补充不改变本次镜像核查的事实或验证范围。

## 控制库与工作空间

- 源码目录：`/root/DOGZILLALib`，`setup.py` 声明版本 3.1.9。
- 已安装库：`/usr/local/lib/python3.10/dist-packages/DOGZILLALib-3.1.9-py3.10.egg`。
- 已读取 egg 内的 `DOGZILLALib/DOGZILLALib.py`，与源码对应文件 SHA256 相同：`3d05141c71b1066e2274cb0d842bd45b328c6d57a9032b7484494433b185585d`。
- AST 静态检查确认存在 `read_imu_raw`、`stop`、`mark_time`、`move`、`turn` 方法定义。这解决了“仅有旧 2.0.7 库而缺少 read_imu_raw”的证据缺口，但未验证返回数据、物理单位、设备连接、踏步或停车效果。
- 厂商工作空间位于 `/root/yahboomcar_ws`，同时存在 `src`、`build`、`install`、`log`；`src` 内还存在嵌套的 `install` 产物，不能直接当作干净源码布局。
- 源码与安装树中查到 `oradar_lidar`、`yahboom_base`、`yahboom_dog_joint_state`、`yahboom_description`、`tf_publisher`、`bringup`、`yahboom_bringup`、`yahboom_laser`、`yahboom_app_save_map` 等包，多数 package.xml 版本为 0.0.0；CHAMP 相关包为 0.1.0，`ydlidar_ros2_driver` 为 1.0.1。存在不等于本项目应启动全部组件。
- 在本次查询的 dpkg 包、`/opt/ros/humble` 的 ament 包索引及上述工作空间源码/安装树 package.xml 中，未找到 `slam_toolbox`、`cartographer`、`cartographer_ros`、`nav2_amcl`、`nav2_map_server`、`nav2_collision_monitor`。未穷举镜像所有自定义路径、其他镜像或外部存储，不能据此宣称整块系统卡绝无这些组件。

## 检查方法与限制

临时容器采用 `--rm --network none --read-only --cap-drop ALL --security-opt no-new-privileges`，无宿主目录或机器人设备挂载；显式指定 `/bin/bash --noprofile --norc` 或 `/usr/bin/python3` 为入口，只运行版本读取、目录清单、XML/源码解析。未启动 ROS daemon、未构建工作空间或执行录包回放。检查后 `docker ps -a` 为空，临时容器已清理，SSH 已退出。

中途 Python 元数据列举遇到 egg 中不存在的 setup.py 记录，随后直接读取 zip 实际文件并完成库接口核对；不把该次中断当作控制库损坏。最初尝试 `/home` 下工作空间为空，实际路径已修正为 `/root`。

## 对共同基线的影响

1. 保留 Debian 宿主、使用厂商 Ubuntu 22.04 / Humble 容器，与目标 Python 3.10 基线相容，无需仅因宿主 Python 3.11 而重装。
2. GCC/G++ 版本已取得；C++17 构建和 ROS 组件兼容尚未实际编译验证。
3. 厂商控制库与设备包有真实可用的调查对象；下一步核对接口与构建/运行前置，而非继续依据旧公开库推断缺失能力。
4. 建图算法环境尚未证实完整，需要进一步确定可复用安装来源与方案，不能宣称镜像开箱即可实现建图。

本文不保存登录密码，不修改项目算法选型或发布 issue。
