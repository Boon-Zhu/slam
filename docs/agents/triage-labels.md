# Triage 标签

工程 skill 使用五种规范 triage role。本文件把每种 role 映射到 GitHub 实际 label 和本地 Markdown 状态值。

| 规范 role | GitHub label | 本地 `Status:` | 含义 |
| --- | --- | --- | --- |
| `needs-triage` | `needs-triage` | `needs-triage` | 维护者需要评估该 issue |
| `needs-info` | `needs-info` | `needs-info` | 等待报告者补充信息 |
| `ready-for-agent` | `ready-for-agent` | `ready-for-agent` | spec 完整，可由智能体自主处理 |
| `ready-for-human` | `ready-for-human` | `ready-for-human` | 需要人工实现 |
| `wontfix` | `wontfix` | `wontfix` | 不会处理 |

两个记录位置都应同步状态。把本地 ticket 提升到 GitHub 时，将当前状态复制为该 issue 的 GitHub label；GitHub triage 状态发生变化时，若对应本地草稿仍存在，也应同步更新。
