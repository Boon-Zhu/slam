# Git 提交与协作规范

## 分支与任务

保留 `main` 和 `develop` 两条长期分支。A/B/C/D 保持模块职责，每个具体任务使用短期分支，不长期维护固定模块分支。

| 分支 | 生命周期 | 起点与合入方向 | 合入条件 |
| --- | --- | --- | --- |
| `main` | 长期 | 接收 `develop` 的交付 PR 和紧急修复 PR | 审查、适用 CI、交付验收 |
| `develop` | 长期 | 初始从 `main` 创建，接收日常任务 PR | 至少一名非作者审查、适用 CI |
| `feature/*` | 短期 | `develop` → `develop` | 一个功能或可验证的小阶段 |
| `fix/*` | 短期 | `develop` → `develop` | 常规缺陷修复 |
| `hotfix/*` | 短期 | `main` → `main`，随后同步回 `develop` | 已交付版本的紧急修复 |
| `docs/*` | 短期 | `develop` → `develop` | 文档变更 |
| `chore/*` | 短期 | `develop` → `develop` | 工具与维护任务 |

- `main` 与 `develop` 均通过 PR 接收变更，不直接推送修改。
- 一个任务分支对应一个可审查、可验证的变化；尽量拆到一两天能交付的小阶段，此时间为拆分参考，不是硬性期限。
- 分支名描述任务，例如 `feature/device-ms200-adapter`、`feature/slam-map-save`、`feature/protection-scan-timeout`。
- 任务合入后删除分支；下一任务从最新 `develop` 创建，紧急修复从最新 `main` 创建。
- 在开发期间及时同步目标分支，及早发现接口与集成问题；不等待整个模块完成后才首次集成。
- 实际多人联调在 `develop` 进行；D 的任务分支仅用于对应的集成开发任务。

## 提交消息

PR 标题及最终 squash 提交必须遵循 Conventional Commits；开发过程的临时提交可以宽松处理。自动生成的分支合并提交不强制套用此格式。

```text
<type>(<scope>): <描述>
```

- 常用类型：`feat`、`fix`、`refactor`、`test`、`docs`、`build`、`ci`、`chore`。
- `scope` 可选，优先使用有意义的模块名，例如 `device`、`slam`、`protection`、`integration`。
- 描述可以使用中文，明确说明变化；不兼容接口变化使用 `!` 或 `BREAKING CHANGE` 标记，并说明影响。

```text
feat(protection): 增加雷达数据超时停车
fix(slam): 拒绝保存无效启动位姿
docs(workflow): 明确任务分支合入规则
```

## PR 审查与合并

| 方向 | 合并方式 |
| --- | --- |
| 短期任务分支 → `develop` | Squash merge |
| `hotfix/*` → `main` | Squash merge，之后通过 `main` → `develop` 同步 |
| `develop` → `main` | Merge commit |
| `main` → `develop` | Merge commit |

- Squash 后结束原任务分支，不继续复用它提交后续 PR。
- `develop` 完成整体验收后通过 PR 合入 `main`；交付记录或热修复通过合并同步回 `develop`，保留长期分支的共同历史。交付同步后内容一致，不要求两个分支指向同一提交。
- PR 关联已有需求 issue，说明解决的问题、验证方式和剩余限制。需求记录遵循 [Issue tracker 约定](issue-tracker.md)。
- 跨模块接口变化由相关模块负责人参与审查，并按 README 第 6.3 节与 D 共同确认；普通模块内部修改无需全部集中到 D 审核。
- CI 的具体检查项尚待实施计划确定。规范要求不代表远端分支保护或 CI 已配置；未执行的检查必须明确标注。
- 真机停车、运动响应等验收不能由 CI 或录包回放代替。

## Agent 编写 PR 正文

- 编写或更新 PR 正文时，必须读取并使用 `mattpocock-skills:pr`；技能描述为 `Use when writing a PR body.`，无需用户每次显式点名。
- 从当前会话的技能目录定位 `SKILL.md`；当前环境路径为 `/home/boon_zhu/.codex/skills/mattpocockskills/skills/engineering/pr/SKILL.md`，其他环境以实际安装位置为准。
- 路径失效时先查找技能；确实不可用时明确告知用户缺少该技能，暂停依赖它的 PR 正文工作，不声称已经遵循技能。
- 正文保留技能的 `Summary`、`Evidence`、`Merge Danger` 三部分：最小必要的图示或 diff、真实的 Before/After 证据、可逆性与影响范围。具体模板以技能为准。
- 使用 `GLOSSARY.md` 中的领域用语（文件存在时）；正文简洁，以中文为主。
- 证据只包含实际观察或执行结果；未执行的测试或缺失的 Before 证据如实标注，不编造失败或通过记录。

## 参考

- [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/)
- [GitHub PR 合并方式](https://docs.github.com/en/pull-requests/reference/pull-request-merges)
