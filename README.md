# Interp & Coding Tracker

追踪 **AI 可解释性** 前沿，并积累 **实践 coding 技巧** 的个人知识库：
自动抓取 + Markdown 知识库 + 可视化看板，三者合一。

```
自动抓取 (GitHub Actions 每天)          手动沉淀                       浏览
arXiv / 博客 RSS / GitHub Releases ─┐
                                    ├─► data/items.json ──┐
              config/sources.yaml ──┘   digests/周报.md    ├─► site/ 看板 (GitHub Pages)
                     tips/ 技巧卡片  ─┐                    │
              notes/papers/ 论文笔记 ─┴─► data/tips.json ──┘
                       experiments/ 可运行的实验脚本
```

## 目录

| 路径 | 内容 |
|---|---|
| `config/sources.yaml` | 追踪哪些来源、关键词过滤、自动打标签规则 |
| `tracker/` | 抓取 / 去重 / 打标签 / 周报 / 索引 的 Python 代码 |
| `data/items.json` | 抓取到的全部条目（Actions 自动更新） |
| `digests/` | 每周一自动生成的周报，带复选框 |
| `tips/interp-experiments/` | 可解释性实验技巧（TransformerLens、patching、SAE…） |
| `tips/ai-assisted-coding/` | 用 coding agent 写代码的工作流与提示技巧 |
| `tips/engineering/` | 通用工程实践（张量形状、可复现性…） |
| `notes/papers/` | 论文精读笔记（从 `_template.md` 复制） |
| `experiments/` | 小而能跑的复现脚本 |
| `site/index.html` | 看板：搜索、按方向/标签筛选、已读/收藏 |

## 快速开始

```bash
pip install -r requirements.txt -r requirements-dev.txt
```

```bash
python -m tracker all        # 抓取 + 周报 + 索引卡片 + 同步看板数据
```

```bash
python -m http.server -d site 8000   # 打开 http://localhost:8000
```

```bash
python -m pytest -q          # 离线单元测试
```

## 日常使用

1. **每天**：Actions 自动抓取，打开看板浏览新条目，点"收藏"标记值得精读的。
2. **每周一**：`digests/` 里出现新周报，勾选读过的条目。
3. **沉淀**：
   - 读完一篇论文 → 复制 `notes/papers/_template.md`，写完后删掉 `draft: true`
   - 学到一个技巧 → 在 `tips/<方向>/` 下新建卡片（参照现有卡片的 front matter）
   - 想动手验证 → 在 `experiments/` 写一个能在小模型上几分钟跑完的脚本
4. **调整来源**：编辑 `config/sources.yaml`，不需要改代码。

### 卡片格式

```markdown
---
title: 标题
track: interp          # interp | ai-coding | engineering
tags: [sae, patching]
date: 2026-11-04
source: https://...    # 可选
---
正文（Markdown）
```

## 部署到 GitHub Pages

1. 推送到 GitHub 后，进入 **Settings → Pages**，把 Source 设为 **GitHub Actions**。
2. **Settings → Actions → General → Workflow permissions** 选 **Read and write**（用于提交抓取到的数据）。
3. 在 **Actions** 页面手动运行一次 `Fetch & publish`。

> 看板里的"已读/收藏"保存在你浏览器的 localStorage 中，只对本机本浏览器有效。
