---
title: 解读 SAE feature 的检查清单
track: interp
tags: [sae, superposition]
date: 2026-11-04
source: https://transformer-circuits.pub/2023/monosemantic-features
---

找到一个"看起来像某概念"的 SAE feature 后，在下结论之前逐项检查：

- [ ] **Top activations 之外**：再看不同激活强度分位（比如 25%、50%、75%）上的样本，确认含义在弱激活时还成立。
- [ ] **反例**：自己构造应该激活、不应该激活的输入，各测一遍。
- [ ] **重建质量**：检查 SAE 在这一层的 reconstruction loss / 把 SAE 输出替换回模型后的 CE loss 增量。重建差的 SAE，其 feature 不可信。
- [ ] **L0 / 死 feature 比例**：L0 太大 → feature 偏稠密、难解释；死 feature 太多 → 字典没训好。
- [ ] **因果验证**：沿 decoder 方向做 steering 或 ablation，行为是否按预期变化？
- [ ] **Feature splitting**：换一个更大字典的 SAE，这个概念可能会裂成好几个更细的 feature。
- [ ] **Auto-interp 只当参考**：LLM 生成的解释要用 detection/fuzzing 打分，不要直接采信。

**工具**：SAELens（加载预训练 SAE、训练）、Neuronpedia（在线浏览 feature）。SAELens 不同大版本的 `SAE.from_pretrained` 返回值不一样（老版本返回 `(sae, cfg, sparsity)` 元组），按你安装的版本查文档。
