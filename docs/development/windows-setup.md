# Windows 开发环境配置指南

更新日期：2026-11-06。面向尚未安装 WSL2 的 Windows 开发者。

本文提供基础环境安装与自检步骤，依据[阶段决议](../architecture/interface-baseline-decisions.md)和官方安装文档编写；尚未在一台全新 Windows 电脑上逐步实测。执行时逐节确认结果，失败后先排查，不继续叠加安装。

## 1. 环境要求与边界

新成员采用 **Windows → WSL2 Ubuntu 22.04 → ROS2 Humble**，Git、SSH、GitHub CLI 和 Python 均在该 Ubuntu 中使用。此路径无需先安装 Docker。

| 项目 | 要求 |
| --- | --- |
| Windows | 优先使用仍获支持的 Windows 11，具备管理员权限并启用硬件虚拟化；WSL 安装命令的最低系统条件见下文微软文档 |
| Linux | WSL **2**，明确选择 Ubuntu **22.04 LTS**，不使用未指定版本的默认 Ubuntu |
| ROS2 | **Humble**；本指南安装 desktop 包，包含基础工具、演示节点与 RViz |
| Python | **3.10.x**，使用 Ubuntu 22.04 系统解释器；补丁版本记录到本机清单 |
| C++ | 按需使用 **C++17**，不要求重写上游组件 |
| 构建与依赖 | colcon、rosdep；实际项目依赖与构建入口以仓库后续配置为准 |
| GitHub CLI | 在 WSL 安装官方稳定版 `gh`，用本人账号登录并获得仓库访问权限 |
| SSH | 在 WSL 使用 OpenSSH 客户端和个人密钥；GitHub 认证与机器人登录分别验证 |
| Python 检查工具 | 固定 **Ruff 0.17.4、mypy 2.4.1、pytest 8.4.2**，目标 Python 3.10；项目检查范围、类型边界及 CI 配置仍待落实 |

上述工具版本于 2026-11-06 在 Ubuntu 22.04.5 / Python 3.10.12 / ROS2 Humble 开发容器中验证：Ruff 格式与 lint、纯 Python 的 mypy 检查、rosdep 依赖检查及最小 `ament_python` 包构建通过；pytest 直接执行及经 colcon 执行均通过纯逻辑、ROS 消息收发、launch 进程测试，共 3 项。这不代表本指南已在全新 Windows 环境完整验证，也不代表项目业务包或机器人通过验收。

工具使用基于系统 Python 3.10、带 `--system-site-packages` 的 venv，ROS 测试保留 Humble 环境设置，使系统 ROS 依赖可见；不覆盖系统自带的 pytest。执行 colcon 测试时须显式使用该 venv 的 `python -m colcon test`，直接运行系统 `colcon` 不会自动选用 venv 中的 pytest。此前 pytest 9.2.0 在当前 Humble `launch_testing` 插件加载阶段发生 hook 接口冲突，因此固定为已通过最小验证的 8.4.2。

当前 Humble 的 `rclpy`、`std_msgs` 未提供 mypy 可用的完整类型声明，直接检查其导入会报告 `import-untyped`。这不影响已经验证的 ROS 运行与测试，但 ROS 接口的静态类型检查仍需配置类型边界；不能将纯 Python 检查通过视为 ROS 接口已获得完整类型检查。

此指南不改变现有设备分工：电脑 1 保留 WSL2 Ubuntu 26.04，计划用 22.04/Humble 容器开发；电脑 2 按阶段决议使用原生 Ubuntu 22.04。新成员无需复制电脑 1 的历史 SSH 绕行参数。

机器人保留 Debian 12 / arm64 宿主与厂商 Ubuntu 22.04.4 / Humble 容器，已核实 Python 为 3.10.12，详见[环境核查报告](../report/pi5-image-version-audit-2026-11-02.md)。开发电脑的安装命令不能直接用于升级机器人；x86 构建产物不能直接作为 ARM 运行产物部署。

## 2. 安装 WSL2 与 Ubuntu 22.04

**执行位置：以管理员身份打开 Windows PowerShell。**

```powershell
wsl --install -d Ubuntu-22.04
```

按提示重启 Windows。首次启动 Ubuntu 时创建自己的 Linux 用户名和密码；密码输入时不显示字符，属于正常行为。

重启后在 PowerShell 检查：

```powershell
wsl --update
wsl --list --verbose
```

预期 `Ubuntu-22.04` 的 `VERSION` 为 `2`。仅当显示为 `1` 时执行：

```powershell
wsl --set-version Ubuntu-22.04 2
```

进入指定发行版：

```powershell
wsl -d Ubuntu-22.04
```

若下载卡住，可按微软文档尝试 `wsl --install --web-download -d Ubuntu-22.04`；出现虚拟化相关错误时，先检查 BIOS/UEFI 虚拟化与 Windows 组件。不要用卸载发行版作为日常排障方式，已有数据会受影响。

来源：[微软 WSL 安装说明](https://learn.microsoft.com/en-us/windows/wsl/install)、[Ubuntu WSL 安装说明](https://ubuntu.com/wsl/docs/latest/howto/install-ubuntu-wsl2/)。

## 3. 初始化 Ubuntu 与 Python

**从本节起，除明确注明外，命令均在 Ubuntu 的 Bash 终端执行，不在 PowerShell 或 Git Bash 执行。**

```bash
cat /etc/os-release
uname -m
sudo apt update
sudo apt upgrade
sudo apt install -y locales software-properties-common curl ca-certificates \
  git openssh-client python3 python3-venv python3-pip build-essential cmake
sudo locale-gen en_US en_US.UTF-8
sudo update-locale LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8
export LANG=en_US.UTF-8
python3 --version
```

确认系统为 `22.04`、Python 为 `3.10.x`。如果不匹配，先确认进入了正确的 WSL 发行版；不要给 24.04/26.04 添加 Jammy 源，也不要替换 `/usr/bin/python3` 来强行匹配。

ROS 的 Python 包使用系统解释器。基础验证阶段先不启用 Conda 或自建 venv；后续工具隔离环境按团队固定版本方案配置，避免全局 `sudo pip install` 覆盖系统及 ROS 依赖。

## 4. 安装并验证 ROS2 Humble

下面使用官方 `ros2-apt-source` 包配置软件源。版本查询需要访问 GitHub；查询、下载或安装失败时先停止本节并排查网络。

```bash
sudo add-apt-repository -y universe
ros_source_version="$(curl -fsSL https://api.github.com/repos/ros-infrastructure/ros-apt-source/releases/latest | python3 -c 'import json,sys; print(json.load(sys.stdin)["tag_name"])')"
```

确认版本变量非空后再下载安装源配置：

```bash
if [ -n "$ros_source_version" ]; then
  curl -fL -o /tmp/ros2-apt-source.deb \
    "https://github.com/ros-infrastructure/ros-apt-source/releases/download/${ros_source_version}/ros2-apt-source_${ros_source_version}.jammy_all.deb" &&
    sudo dpkg -i /tmp/ros2-apt-source.deb
else
  echo '未取得 ros2-apt-source 版本，请先检查网络。'
fi
```

确认上一步成功后：

```bash
sudo apt update
sudo apt upgrade
sudo apt install -y ros-humble-desktop ros-dev-tools
source /opt/ros/humble/setup.bash
```

让后续新开的 Bash 终端自动加载 Humble（重复执行不会重复追加）：

```bash
grep -qxF 'source /opt/ros/humble/setup.bash' ~/.bashrc || \
  printf '\nsource /opt/ros/humble/setup.bash\n' >> ~/.bashrc
```

初始化 rosdep；全新环境只需执行一次 `sudo rosdep init`，后续仅运行普通用户的 `rosdep update`。若提示已初始化，保留现有配置并继续更新。

```bash
sudo rosdep init
rosdep update
printenv ROS_DISTRO
python3 -c 'import sys, rclpy; print(sys.version); print(rclpy.__file__)'
colcon --help
```

预期发行版为 `humble`，Python 为 3.10，能导入 `rclpy`。然后打开两个 Ubuntu 终端，分别执行：

```bash
# 终端 1
ros2 run demo_nodes_cpp talker
```

```bash
# 终端 2
ros2 run demo_nodes_py listener
```

预期 talker 发布消息、listener 持续接收；验证完成后在两边按 `Ctrl+C`。这只验证本机 ROS 通信，不证明与机器人跨机通信或项目功能已经可用。

需要图形界面时运行 `rviz2`；若显示失败，先确认 WSLg 与显卡条件，基础命令行验证可以独立完成。参见[微软 WSL GUI 说明](https://learn.microsoft.com/en-us/windows/wsl/tutorials/gui-apps)。

来源：[Humble 官方安装说明](https://docs.ros.org/en/humble/Installation/Ubuntu-Install-Debs.html)、[官方源配置源码](https://github.com/ros2/ros2_documentation/blob/humble/source/Installation/_Apt-Repositories.rst)。本文未锁定滚动更新的 apt 包补丁版本；安装完成后记录实际版本，后续按项目依赖锁定方案对齐。

## 5. 安装 GitHub CLI

使用 GitHub CLI 官方 apt 源，不把其他成员机器上的 `gh` 版本或账号作为本机配置。以下每步成功后再执行下一步：

```bash
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL -o /tmp/githubcli-archive-keyring.gpg \
  https://cli.github.com/packages/githubcli-archive-keyring.gpg
sudo install -m 0644 /tmp/githubcli-archive-keyring.gpg \
  /etc/apt/keyrings/githubcli-archive-keyring.gpg
printf 'deb [arch=%s signed-by=/etc/apt/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main\n' \
  "$(dpkg --print-architecture)" | sudo tee /etc/apt/sources.list.d/github-cli.list
sudo apt update
sudo apt install -y gh
gh --version
git --version
ssh -V
```

来源：[GitHub CLI 官方 Linux 安装说明](https://github.com/cli/cli/blob/trunk/docs/install_linux.md)。

## 6. 配置个人身份、SSH 与 GitHub 登录

先把示例姓名和邮箱替换为自己的信息；邮箱可使用 GitHub 账号提供的 noreply 地址。

```bash
git config --global user.name '你的名字'
git config --global user.email '你的 GitHub 提交邮箱'
ls -la ~/.ssh
```

全新用户没有 `.ssh` 目录属于正常情况。仅在没有现有个人密钥时生成新密钥；若提示覆盖已有文件，先取消并检查。

```bash
ssh-keygen -t ed25519 -C '你的 GitHub 提交邮箱'
```

按提示使用默认路径 `~/.ssh/id_ed25519`，设置自己的口令。将密钥加载到当前 shell 的 SSH agent：

```bash
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/id_ed25519
gh auth login --hostname github.com --git-protocol ssh --web
```

登录时允许上传刚生成的**公钥**，核对浏览器中的账号并完成授权；WSL 无法自动打开浏览器时，在 Windows 浏览器打开终端给出的地址，输入一次性代码。若跳过了公钥上传，按 [GitHub 添加公钥说明](https://docs.github.com/en/authentication/connecting-to-github-with-ssh/adding-a-new-ssh-key-to-your-github-account)手动添加 `~/.ssh/id_ed25519.pub`。

私钥留在本机，不复制到仓库或发送给他人。新终端如果没有可用的 agent，会再次需要 `ssh-add`；上面的启动方式不是持久化服务配置。

```bash
gh auth status
ssh -T git@github.com
gh api repos/Boon-Zhu/slam --jq '{full_name,permissions}'
```

首次 SSH 连接时，对照 [GitHub 公布的主机指纹](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/githubs-ssh-key-fingerprints)确认后接受。预期返回包含本人用户名的认证成功消息；GitHub 不提供 shell，此测试退出码为 1 是正常行为。[官方 SSH 测试说明](https://docs.github.com/en/authentication/connecting-to-github-with-ssh/testing-your-ssh-connection)

`gh` 登录成功不代表仓库权限已授予；若仓库 API 无法访问，确认账号、团队邀请和网络。GitHub CLI 的 API 认证与 Git 的 SSH 认证是两条链路，应分别检查。登录参数详见 [gh auth login](https://cli.github.com/manual/gh_auth_login)。

## 7. 克隆仓库与常用操作

在 WSL 的 Linux 文件系统中工作，使用自己的 home 路径；不要照搬其他成员的 `/home/<用户名>`。项目放在 `~/project`，避免默认放入 `/mnt/c`；参见[微软文件存储建议](https://learn.microsoft.com/en-us/windows/wsl/filesystems)。

```bash
mkdir -p ~/project
cd ~/project
git clone git@github.com:Boon-Zhu/slam.git
cd slam
git remote -v
git ls-remote origin HEAD
gh issue list --repo Boon-Zhu/slam
gh pr list --repo Boon-Zhu/slam
```

Git 推送优先 SSH，issue/PR 优先 `gh`。既有仓库若为 HTTPS remote，`gh auth login --git-protocol ssh` 不会自动改写它；先检查实际 URL，再按需要调整，不能假定协议已经切换。

开始任务前阅读根目录 [AGENTS.md](../../AGENTS.md) 与 [Git 协作规范](../agents/git-workflow.md)，确认远端分支后从 `develop` 创建短期任务分支。以下仅为已经完成任务、准备提交 PR 时的用法，不是安装自检步骤：

```bash
git push -u origin HEAD
gh pr create --repo Boon-Zhu/slam --base develop \
  --title 'docs(setup): 完善环境配置说明' --body-file /tmp/pr-body.md
```

执行前确认当前是任务分支、目标正确，且已准备实际变更对应的标题和正文文件；agent 编写正文必须使用 `mattpocock-skills:pr`。不要为了测试环境向 `main` 或 `develop` 推送。

本指南只安装基础工具，不预设仓库尚未落地的 ROS package 路径或测试命令。项目依赖、`rosdep install` 范围、colcon 构建入口和 Python 工具固定版本，以后续仓库配置为准。

## 8. 机器人访问与部署边界

首阶段通过 SSH 在机器人上启动真机节点，开发电脑取回日志和录包进行分析；跨设备 DDS/RViz 通信另行验证。请向 A/D 获取实际地址、用户名、端口、主机指纹及登录方式，本指南不猜测默认账号或密码。

将下面的占位值替换成 A/D 提供的信息后，追加到 WSL 的 `~/.ssh/config`，不覆盖已有配置：

```sshconfig
Host dogzilla
    HostName ROBOT_IP
    User ROBOT_USER
    Port 22
```

`Port` 按实际端口修改；如已为机器人单独配置密钥，再增加对应 `IdentityFile`。登录后先只读检查：

```bash
ssh dogzilla
# 以下在机器人 SSH 会话内执行
hostname
cat /etc/os-release
exit
```

以上只能确认宿主与登录；ROS 位于厂商容器，不能在宿主找不到 `ros2` 时直接安装或重装。部署路径、容器启动、版本切换和依赖变更由 D 协调。本阶段不需要在开发电脑安装 SSH server，也不需要给 Windows 开放入站 SSH。

## 9. 记录与完成条件

在仓库根目录创建 `.local/environment.md`，按自己的检查结果填写。`.local/` 已由仓库忽略，确认 `git check-ignore .local/environment.md` 有输出；文件中不保存令牌、私钥或密码。

```markdown
# 本机开发环境

检查日期：YYYY-MM-DD
设备/负责人：填写本人设备标识

- Windows / WSL 版本：填写 PowerShell 检查结果
- Ubuntu / 架构：填写 /etc/os-release 与 uname -m 结果
- ROS：Humble；基础收发测试：通过 / 失败 / 未执行
- Python：填写 python3 --version；rclpy 导入：通过 / 失败
- gh / Git / OpenSSH：填写实际版本
- GitHub 账号与仓库权限：填写账号和所需权限是否具备，不粘贴凭据
- Git remote：填写 URL；SSH 认证与仓库读取：通过 / 失败
- Docker：本路径非必需；如有使用，记录实际镜像与验证状态
- 机器人 SSH：未配置 / 已验证；必要时记录本机连接别名
- 项目构建、回放、真机验证：分别填写，未执行就标未执行
- 当前阻塞与特殊配置：填写问题、临时处理方式及适用范围
```

完成基础部署的标准：WSL2/Ubuntu 22.04 与 Python 3.10 版本匹配，Humble 双终端演示通过，GitHub CLI 能读取仓库，SSH 能认证并读取 Git remote，本机记录已填写。机器人 SSH 可在拿到设备后单独完成；基础部署完成不代表项目构建或真机验收通过。

## 10. 常见问题

| 现象 | 优先检查 |
| --- | --- |
| `ros2: command not found` | 是否进入 Ubuntu-22.04，是否安装成功及 source Humble；机器人宿主另按容器方案处理 |
| Python 版本不符或 `import rclpy` 失败 | 是否误用了 Windows Python、Conda/venv 或错误 WSL 发行版 |
| `gh` 报认证失败 | 核对网络、当前账号及 `gh auth status`；agent 沙箱受限时按权限流程重试，不直接认定令牌失效 |
| SSH `Permission denied (publickey)` | 公钥是否属于当前 GitHub 账号、`ssh-add -l` 是否包含预期密钥、仓库权限是否具备 |
| SSH 配置权限错误 | 检查错误指向的配置文件归属和权限；不要把其他设备的 `-F /dev/null` 绕行参数写成全员默认设置 |
| SSH 超时但 HTTPS/API 可用 | 检查网络是否限制 22 端口；按 [GitHub SSH over HTTPS 说明](https://docs.github.com/en/authentication/troubleshooting-ssh/using-ssh-over-the-https-port)核实 443 方案后配置 |
| talker/listener 正常但无法连接机器人 ROS | 本机演示不覆盖跨机 DDS；首阶段先用 SSH，跨机通信按需求单独验证 |

后续若项目提供固定开发镜像或依赖锁定文件，应更新本指南，区分基础安装成功与团队统一版本验证完成。
