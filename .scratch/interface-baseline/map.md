## Destination

形成模块可以据此独立细化方案的共同基线，包括版本范围、职责与故障语义、公共技术栈和质量要求。

## Notes

这是 2026-11-01 至 2026-11-02 已完成讨论的追溯归档；此前按用户要求等待成员 ID 齐全，未在线建立 map。不是重新开展一轮决策，也不表示实现或验证完成。采用 wayfinder 与 domain-modeling；一次讨论一个共同问题。

A：ZWC-Maker（4），B：Boon-Zhu（3），C：NeuviFuri1115（1），D：zer0-2w（2）。成员可互助。

## Decisions so far

- [共同基线决议：版本、模块职责、故障语义与工程约束](https://github.com/Boon-Zhu/slam/issues/3): 共同职责、版本取舍、运行语义与工程约束已确认，详情见 resolution comment。

## Not yet specified

本轮目的内无待继续讨论的问题。具体接口由提供方、使用方与 D 逐项确认；研究发现冲突时新开 issue，不把未经验证能力视为已实现。

## Out of scope

模块内部选型、设备采集与真机验证、具体 CI 配置、交付版细化和具体日期安排移交普通 issue，不作为本轮 map 的开放子决策。agent 开发流程不在本轮范围。

后续移交：

- [A：核实设备数据并完成首次全量采集方案](https://github.com/Boon-Zhu/slam/issues/4)
- [A：核实停止、踏步与 A 失效时的原装断电能力](https://github.com/Boon-Zhu/slam/issues/5)
- [B：选择快速验证版运动估计与建图组件](https://github.com/Boon-Zhu/slam/issues/6)
- [B：细化单地图完整保存及 D 调用契约](https://github.com/Boon-Zhu/slam/issues/7)
- [C：细化持续操作、障碍限制与故障响应方案](https://github.com/Boon-Zhu/slam/issues/8)
- [D：细化用户入口、状态反馈与试运行日志核对](https://github.com/Boon-Zhu/slam/issues/9)
- [D：落实机器人环境与开发 CI 最小试运行方案](https://github.com/Boon-Zhu/slam/issues/10)
- [交付版：细化定位、多地图与完整故障验收范围](https://github.com/Boon-Zhu/slam/issues/11)
- [D：记录团队讨论后的集成日期与里程碑安排](https://github.com/Boon-Zhu/slam/issues/12)
