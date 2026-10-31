# Issue tracker：GitHub 与本地 Markdown

GitHub issue tracker 是本仓库中具有权威性的团队共享记录。`.scratch/` 下的本地 Markdown 文件同样受支持，用于早期 spec、调查笔记和低成本的 ticket 草稿。当任务可能存在本地对应文件时，智能体必须同时检查 GitHub 与本地 Markdown。

如果 GitHub 与本地 Markdown 不一致，以当前 GitHub issue 所确认的范围和决策为准。实现依赖某项决策前，应先把本地结论同步到 GitHub；不得把未共享草稿静默视为团队共识。

## 选择记录位置

- **发布团队必须看到的 spec、ticket 或决策：** 创建或更新 GitHub issue。
- **记录本地草稿或调查：** 写入 `.scratch/<功能标识>/`。
- **把本地 ticket 或 spec 提升为共享工作：** 保留 Markdown 文件作为工作材料，同时创建对应的 GitHub issue，并在文件中可以共享时附上摘要和链接。
- **获取指定的本地 ticket：** 直接读取给定路径。
- **获取指定的 GitHub issue 或 PR：** 使用下文命令。
- **triage：** GitHub 上使用规范 label，本地 Markdown 使用对应的 `Status:` 值。

## GitHub 约定

- **创建 issue：**`gh issue create --title "..." --body "..."`。正文有多行时使用 heredoc。
- **读取 issue：**`gh issue view <编号> --json number,title,body,labels,comments`。
- **列出 issue：**`gh issue list --state open --json number,title,body,labels,comments --jq '[.[] | {number, title, body, labels: [.labels[].name], comments: [.comments[].body]}]'`，并按需要使用 `--label` 与 `--state` 过滤。
- **把 issue 设为父 issue 的子 issue：**`gh issue create --parent <父 issue> ...`，或先创建后再运行 `gh issue edit <父 issue> --add-sub-issue <子 issue>`（要求 `gh` 2.94 及以上）。旧版 `gh` 可运行 `gh api --method POST repos/<负责人>/<仓库>/issues/<父 issue>/sub_issues -F sub_issue_id=<子 issue 数据库编号>`。不支持子 issue 时，在子 issue 正文顶部写 `Part of #<父 issue>`。
- **阻塞关系：** 以 GitHub 原生 issue 依赖为权威表示。使用 `gh issue create --blocked-by <n>,<n> ...` 或 `gh issue edit <子 issue> --add-blocked-by <阻塞 issue>` 建立关系（要求 `gh` 2.94 及以上）。旧版 `gh` 可运行 `gh api --method POST repos/<负责人>/<仓库>/issues/<子 issue>/dependencies/blocked_by -F issue_id=<阻塞 issue 数据库编号>`；其中编号不是 issue 的 `#` 编号或 `node_id`。不支持依赖时，在子 issue 正文顶部写 `Blocked by: #<n>, #<n>`。
- **统计未关闭的阻塞项：**`gh api repos/<负责人>/<仓库>/issues/<n> --jq .issue_dependencies_summary.blocked_by`。
- **评论 issue：**`gh issue comment <编号> --body "..."`。
- **添加或移除 label：**`gh issue edit <编号> --add-label "..."` 或 `--remove-label "..."`。
- **关闭 issue：** 先用评论写明结论，再运行 `gh issue close <编号>`。对已经关闭的 issue 使用 `gh issue close --comment` 会丢弃评论，因此采用两步操作。

从 `git remote -v` 推断仓库；在克隆目录内运行时，`gh` 会自动识别。issue 只能创建在本仓库 `Boon-Zhu/slam`，不得创建到 skill 来源仓库。

## 本地 Markdown 约定

- 每个功能或工作主题使用独立目录：`.scratch/<功能标识>/`。
- spec 文件为 `.scratch/<功能标识>/spec.md`。
- 每个 ticket 单独一个文件：`.scratch/<功能标识>/issues/<NN>-<标识>.md`，从 `01` 开始编号。不得把互不相关的 ticket 合并到一个文件。
- 文件顶部附近写 `Status:`，值使用规范 triage 状态。
- 讨论历史追加到 `## Comments` 标题下。
- 除非团队明确决定提交，否则这些文件属于本地工作材料。

## PR 不作为需求入口

PR 继续用于代码审查和分支合并；外部 PR 不进入 triage 队列，也不自动视为需求。只有 GitHub issue 代表团队共享需求。

## 当 skill 要求“发布到 issue tracker”时

创建 GitHub issue。可以先写本地 Markdown 草稿用于探索，但共享结果必须发布到 GitHub。

## 当 skill 要求“获取相关 ticket”时

提供了本地路径时读取该路径；否则读取指定的 GitHub issue。发现相关本地草稿时应把它作为支持上下文，而不是 GitHub issue 的替代品。

## Wayfinding operations（寻路操作）

- **wayfinder map：** 一个带有 `wayfinder:map` label 的 GitHub issue，正文保存 Notes、Decisions-so-far 与 Fog。
- **子 ticket：** 优先使用 GitHub 子 issue；不可用时加入 wayfinder map 正文的任务列表，并在顶部写 `Part of #<wayfinder map issue>`。
- **阻塞：** 使用 GitHub 原生 issue 依赖；不可用时写 `Blocked by:` 行。
- **frontier ticket：** 按 wayfinder map 顺序选择第一个未关闭、无未解决阻塞且未分配的 ticket。
- **认领：** 使用 `gh issue edit <n> --add-assignee @me` 分配给自己。
- **解决：** 评论答案、关闭 issue，并把上下文指针加入 wayfinder map 的 Decisions-so-far。
