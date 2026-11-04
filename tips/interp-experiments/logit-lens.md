---
title: Logit lens：看每一层"此刻想输出什么"
track: interp
tags: [logit-lens, transformerlens]
date: 2026-11-04
source: https://www.lesswrong.com/posts/AcKRB8wDpdaN6v6ru/interpreting-gpt-the-logit-lens
---

把中间层的残差流直接送进最后的 `ln_final` + `unembed`，就能看到预测是怎样逐层成形的。

```python
logits, cache = model.run_with_cache(prompt)
resid_stack, labels = cache.accumulated_resid(layer=-1, incl_mid=False,
                                              pos_slice=-1, return_labels=True)
resid_stack = cache.apply_ln_to_stack(resid_stack, layer=-1, pos_slice=-1)
layer_logits = resid_stack @ model.W_U          # [n_layers+1, batch, d_vocab]
target = model.to_single_token(" Paris")
print(layer_logits[:, 0, target])
```

**注意**
- 一定要先过 `ln_final`（上面的 `apply_ln_to_stack`），否则不同层的数值没法比较。
- 在早期层效果差，因为那时的表示还没对齐到 unembedding 空间。**Tuned lens**（为每层单独训练一个仿射变换）通常更可靠。
- 完整可运行版本见 `experiments/01_logit_lens.py`。
