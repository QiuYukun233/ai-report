---
title: Explore → Plan → Code → Commit 工作流
track: ai-coding
tags: [agents, claude-code]
date: 2026-11-04
source: https://www.anthropic.com/engineering/claude-code-best-practices
---

适合不那么简单的改动：

1. **Explore**：让 agent 先读相关文件，并明确要求"先不要写代码"。
2. **Plan**：让它写出方案（改哪些文件、为什么这样改、有哪些风险）。你在这一步纠偏，代价最低。
3. **Code**：按方案实现，每完成一部分就跑一次验证。
4. **Commit**：让它写清楚 commit message；需要的话再开 PR。

**提示词技巧**
- 具体比含糊好："给 `store.merge` 加一个测试，覆盖重复 id 的情况"，好过"多加点测试"。
- 直接贴报错原文、文件路径、截图，不要转述。
- 上下文变长、开始跑偏时，清空上下文，带着上一步的计划重新开始，往往比继续纠缠更快。
- 研究型代码（比如可解释性实验）：让它先写一个能在小模型 / 小 batch 上**几秒内跑完**的版本，确认正确后再放大。
