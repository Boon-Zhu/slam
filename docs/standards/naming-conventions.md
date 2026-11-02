# 命名规范

确认日期：2026-11-02。适用于本仓库自研文件、目录、package 与代码标识符；示例用于说明命名，不代表包、接口或实现已经确定。

## 通用原则

- 名称优先表达主题、职责或行为，使用小写英文单词组合；类型和固定入口按下表处理。
- 同一概念使用一致词汇，领域含义遵循根目录 [GLOSSARY.md](../../GLOSSARY.md)。模块职责使用可读名称，不用 `a`、`b` 等分工字母作为 package 或文件的主要名称。
- 使用明确职责，如 `map_store.py`、`pose_validation.py`，避免含糊的 `utils.py`、`common.py`、`manager.py`。
- 临时修订交给 Git 记录，不使用 `new`、`final`、`v2` 区分草稿。确需共存的正式协议或产品版本可以携带有定义的版本标识。

## 文档与目录

| 对象 | 格式 | 示例 |
| --- | --- | --- |
| 普通文档与文档目录 | `kebab-case` | `interface-baseline-decisions.md` |
| 持续维护的文档 | 无日期的主题名 | `upstream-policy-assessment.md` |
| 独立调查、测试快照 | `<主题>-YYYY-MM-DD.md` | `pi5-image-version-audit-2026-11-02.md` |
| ADR | `<四位编号>-<主题>.md` | `0001-module-boundaries-and-motion-path.md` |

文件名供稳定引用，正文使用清晰的中文标题。持续维护文档在正文记录创建或确认日期及后续更新日期；快照记录实际检查日期、对象、版本和验证范围。文件移动或排版修改不改变证据发生日期；新一轮检查保留独立证据，不把旧结论包装成新结果。

相关文档共享主题前缀，如 `upstream-policy-device.md` 与 `upstream-policy-mapping.md`。目录归属、完整清单与维护步骤见[文档索引](../README.md)。

## package、代码与配置

| 对象 | 格式 | 示例 |
| --- | --- | --- |
| 自研 ROS package | `dogzilla_<职责>`，使用 `snake_case` | `dogzilla_mapping` |
| Python 包、模块及代码目录 | `snake_case` | `map_store.py` |
| 函数、公开方法、变量及参数 | `snake_case` | `save_map()`、`map_path` |
| 私有方法 | `_snake_case` | `_build_encoder()`、`_validate_pose()` |
| 类与类型 | `PascalCase` | `MapStore` |
| Python 常量 | `UPPER_SNAKE_CASE` | `DEFAULT_TIMEOUT_S` |
| 配置文件 | `snake_case.yaml` | `mapping.yaml` |
| Python launch 文件 | `snake_case.launch.py` | `mapping.launch.py` |
| Python 测试文件 | `test_<被测对象>.py` | `test_map_store.py` |

Python 私有方法使用单个前导下划线表示内部使用约定；语言规定的特殊方法（如 `__init__`）保留原名。C++ 引入时补齐成员变量、常量、头文件等语言细则，不从 Python 示例推导完整 C++ 规范。

函数和方法用动词表达行为，如 `save_map()`、`load_map()`；布尔值表达可判断状态，如 `is_connected`、`has_valid_pose`；有单位的数值注明单位，如 `timeout_s`、`distance_m`。名称中的动作必须与实际语义一致，尤其要区分“停止移动”“停止行为”和“强制断电”。

## 固定名称与兼容边界

- 固定入口与工具约定保留原名，如 `README.md`、`AGENTS.md`、`GLOSSARY.md`、`CMakeLists.txt`、`package.xml`、`__init__.py`。
- 上游包、厂商文件、外部接口及工具生成的文件保留其命名约定；本规范不授权修改上游代码或破坏接口兼容。
- 本地 ticket 保留 [issue tracker 约定](../agents/issue-tracker.md)中的编号形式；Git 分支遵循 [Git 协作规范](../agents/git-workflow.md)。
- 重命名时同步引用、导入和配置消费方；公开接口的改名需按现有接口协作流程确认。

本文件确立命名约定，不代表 Ruff、mypy、构建或 CI 检查已经配置；其他代码规范仍需按阶段决议落实。
