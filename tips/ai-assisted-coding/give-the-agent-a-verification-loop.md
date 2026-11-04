---
title: 给 coding agent 一个"能自我验证"的闭环
track: ai-coding
tags: [agents, claude-code, testing]
date: 2026-11-04
source: https://www.anthropic.com/engineering/claude-code-best-practices
---

Agent 的产出质量，很大程度取决于它能不能**自己检查对错**。

**做法**
1. **先写（或先让它写）失败的测试**，确认测试真的失败，再让它实现代码直到测试通过。明确告诉它"不要修改测试"。
2. 在项目记忆文件（如 `CLAUDE.md`）里写清楚：怎么跑测试、怎么 lint、怎么启动项目，这样 agent 每次都知道该用什么命令验证。
3. UI 或可视化任务：给它截图能力，或者给一张目标图，让它"截图 → 对比 → 再改"。
4. 让验证命令**又快又安静**：只跑相关测试（`pytest tests/test_x.py -q`），输出简短，agent 才读得过来。

**反模式**
- "帮我把这个功能写完"，但没给任何验收标准 → 它会停在"看起来能跑"的状态。
- 一次让它改一大片 → 难以审查。拆成小步，每步都能单独验证、单独提交。
