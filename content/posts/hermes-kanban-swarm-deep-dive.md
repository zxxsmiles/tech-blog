---
title: "Kanban Swarm：一个不引入第二个调度器的多智能体引擎"
date: 2026-09-21
tags: ["Hermes Agent", "Kanban Swarm", "Multi-Agent", "Orchestration"]
author: zhangxiaoxing
---

先说一句反直觉的话：Hermes Agent 的 Kanban Swarm 并不是 v0.16 带来的。如果你正准备按「v0.16 推出 Kanban Swarm」去写、去讲，你从一开始就会讲错。Swarm v1 实际随 v0.15.0（2026-05-28，The Velocity Release）发布，落地提交 3ee7a5546d，新增的 hermes_cli/kanban_swarm.py 只有约 279 行 Python；而 v0.16.0（2026-06-05，The Surface Release）的主题是原生桌面 App、浏览器后台面板、远程 gateway、模糊模型选择器与 /undo，对 Kanban 只是补了 goal_mode 卡片、任务附件、default_assignee 兜底等运维层能力。本文标题保留 v0.16，但第一件事是把版本关系摆正：Swarm 生于 v0.15.0，v0.16.0 把它周边补全。

<!--more-->

为什么一个多智能体系统只要约 279 行？因为它刻意不引入第二个调度器，也不引入新的状态服务，只往既有 Kanban 内核里写一张小小的任务图。拓扑如下：

```text
root（黑板/审计锚点）
  ├─ worker × N（并行）
  └─ verifier（等所有 worker done）
       └─ synthesizer（等 verifier done）
```

模块 docstring 把意图说得很清楚：It intentionally does not introduce a second scheduler，它 writes a small task graph into the existing Kanban kernel。共享黑板同样 low-tech——不过是 root 任务上的结构化 JSON comment，所有状态都落在既有 task_comments / task_events 行里，于是 dashboard、notifier、/kanban 命令、dispatcher 全部零改动可见。对开发者而言这句话值钱：要加多智能体，不必先加服务。

门控（gate）靠「父依赖 + 状态机」表达，而不是在 prompt 里喊话。verifier 的 parents 等于所有 worker id，synthesizer 的 parents 等于 [verifier]；父任务全部 done 之前，子卡片停在 todo，由 dispatcher 在父完成时提升为 ready。verifier 正文是一条约定式指令：complete only with metadata {"gate": "pass"} when evidence is sufficient，否则 block。这里必须诚实：拓扑级门控是硬约束（依赖引擎强制），但 {"gate": "pass"} 这个判定是提示词层约定，不是代码层校验——在 v0.21.3 代码库检索 "gate"，除卡片正文字符串与测试外没有强制校验逻辑。它拦不住 verifier 偷懒，拦得住的是 synthesizer 在 verifier 完成前启动。

黑板协议 = 一行前缀 + 一个 JSON 对象。前缀常量是 "[swarm:blackboard] "；写入 post_blackboard_update() 本质是 json.dumps({"key": key, "value": value}) 追加为 root 的一条普通 comment；读取 latest_blackboard() 扫全部 comment，按 key 合并、后写覆盖先写。这就是「多智能体共享上下文」的最小形态——没有向量库、没有消息总线，只有同一条 SQLite 行加一个覆盖语义。副作用很实用：命中幂等 key 时，函数先从黑板还原拓扑直接返回，不会重复建图。

整张拓扑在一个事务里提交。create_swarm() 用 with kb.write_txn(conn): 包住建图，仓库测试注入第 3 次 create_task 抛错来验证整图回滚。对自建编排的开发者，这是一条具体实现要求：建图必须是单事务、读者不可见中间态。

worker 是「完整 OS 进程 + 独立 profile 身份」。一张卡就是 ~/.hermes/kanban.db 里的一行，每个 worker 在各自 profile 下 spawn，默认 60s 的 dispatcher tick 内被领取；跑一群 worker 的前提是 dispatcher 在跑（默认由 hermes gateway start 内嵌）。这就是它和进程内 subagent 的根本差别：worker 有独立 profile、独立记忆、独立工作区，能崩溃后 reclaim、能被换模型重跑；代价是你得真正理解 dispatcher 的生命周期与并发上限，否则会在本地 LLM 或限流场景下把任务堆到超时。

那它和 delegate_task 怎么分工？官方一句话：delegate_task is a function call; Kanban is a work queue where every handoff is a row any profile (or human) can see and edit。需要「结果回到当前上下文、无人参与、短推理」用 delegate_task；需要「跨 agent 边界、跨重启存活、可能要人介入、晚点还能被接手审计」用 Kanban。二者可共存。

一条可运行的命令（截至 2026-09 安装版本实测）：

```bash
hermes kanban swarm "Design a multi-region failover plan" \
  --worker researcher:调研 --worker architect:架构 --worker sre:运维 \
  --verifier reviewer --synthesizer writer
```

注意：官方文档示例写的是 --workers researcher,architect,sre，但本机 hermes kanban swarm --help 显示真实参数是可重复的 --worker PROFILE:TITLE[:SKILL,SKILL]，不存在 --workers。文档示例与 CLI 不符，照抄会踩坑。建群时每个 worker 卡片会自动追加一段 Swarm protocol，要求 worker 读 sibling/parent handoff、把机器可读事实放进 completion metadata、把跨 worker 备注写到 root 的结构化 comment。

最后留三个分层入口的现状：/swarm <自然语言> 尚不存在（issue #35600 仍 open，P3，无 PR）；今天能用的正道是显式 CLI hermes kanban swarm --worker ...；triage 自动分解 + dispatcher 自动派发虽然全自动，但产出的是扁平依赖树，不是带 verifier/synthesizer 的门控管线。

Swarm 的价值不在产品功能，而在三个可迁移的设计决策：拓扑、持久化、门控——用一张持久化任务队列，同时拿到门控、崩溃恢复与人工介入。如果你正在评估 OpenAI Swarm、LangGraph、CrewAI 之外的多智能体路线，或已在自建任务队列，这 279 行值得一读。
