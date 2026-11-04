---
title: Activation patching 标准流程（clean / corrupted / logit diff）
track: interp
tags: [patching, circuits, transformerlens]
date: 2026-11-04
source: https://arxiv.org/abs/2309.16042
---

**目的**：找出"哪个组件的激活对模型行为是因果重要的"。

**流程**
1. 构造一对**长度相同**的 prompt：
   - clean：`"When John and Mary went to the store, John gave a drink to"` → 答案 ` Mary`
   - corrupted：把关键信息换掉（比如换成另外一组名字），使正确答案改变
2. 定义指标，推荐用 **logit diff** = `logit[正确] - logit[错误]`，它比概率更线性、更稳定。
3. 用 corrupted 输入跑前向，把**某一个位置的激活换成 clean 时的值**，看指标恢复了多少：
   `score = (patched - corrupted) / (clean - corrupted)`，1 表示完全恢复。
4. 依次扫描 层 × 位置（resid）或 层 × head（attn），画热力图。

```python
from functools import partial
_, clean_cache = model.run_with_cache(clean_tokens)

def patch_resid(resid, hook, pos):
    resid[:, pos] = clean_cache[hook.name][:, pos]
    return resid

for layer in range(model.cfg.n_layers):
    for pos in range(clean_tokens.shape[1]):
        logits = model.run_with_hooks(corrupt_tokens, fwd_hooks=[
            (f"blocks.{layer}.hook_resid_pre", partial(patch_resid, pos=pos))])
        ...  # 计算 logit diff 并记录
```

**要点**
- 方向有两种：denoising（clean 补到 corrupted 上，看"什么是充分的"）和 noising（反过来，看"什么是必要的"），两者结论可能不同。
- corrupted 尽量只改变一个变量；高斯噪声式的 corruption 容易产生分布外的激活。
- 层和 head 多时，先用 attribution patching（梯度线性近似）粗筛，再对候选组件做精确 patch。
- 参考：Zhang & Nanda, *Towards Best Practices of Activation Patching* (2023)。
