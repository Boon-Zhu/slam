# DOGZILLA S2 室内建图与定位

本上下文描述团队在第一版室内建图与定位工作中使用的共同语言，覆盖工程协作与机器人领域。术语定义约束团队文档、issue、ticket、spec 与代码中的命名。

## 术语

### 工程协作

**Skill**:
可按名称调用、为 agent 提供特定工作流程或行为规则的一套指令。
_Avoid_（避免）：笼统的“技能”

**Issue**:
由 issue tracker 持久追踪的一项工作，可以表示缺陷、任务、spec 或 ticket。
_Avoid_（避免）：工单

**Ticket**:
由 `to-tickets` skill 生成的垂直切片工作单元；发布到 GitHub 后由一个 issue 表示。
_Avoid_（避免）：议题、笼统任务

**Spec**:
对问题、解决方式、用户故事、实现决策与测试决策形成的一份完整工作产物；通常作为 issue 发布。
_Avoid_（避免）：普通需求、设计文档

**Triage role**:
在 triage 过程中为 issue 指定的标准生命周期角色；GitHub label 与本地 `Status:` 使用同一组角色名。
_Avoid_（避免）：普通状态标签、任意分类标签

**Wayfinder map**:
由 `wayfinder` skill 维护、作为决策子 issue 索引的单个 issue。
_Avoid_（避免）：单独使用“地图”

**PR**:
请求审查并把代码分支合并到目标分支的代码变更提议；默认不作为需求入口。
_Avoid_（避免）：issue、需求
