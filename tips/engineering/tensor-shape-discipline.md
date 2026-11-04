---
title: 张量代码的形状纪律：einops + 形状注解 + 断言
track: engineering
tags: [pytorch, einops]
date: 2026-11-04
source: https://einops.rocks/
---

可解释性代码里最常见的 bug 是**维度搞错，却没有报错**（比如广播把错误悄悄吞掉了）。

```python
import einops, torch
from jaxtyping import Float
from torch import Tensor

def head_contrib(z: Float[Tensor, "batch pos head d_head"],
                 W_O: Float[Tensor, "head d_head d_model"]) -> Float[Tensor, "batch pos head d_model"]:
    return einops.einsum(z, W_O, "batch pos head d_head, head d_head d_model -> batch pos head d_model")

x = einops.rearrange(x, "b (h d) -> b h d", h=n_heads)   # 比 .view(b, h, -1) 更不容易出错
assert x.shape == (B, n_heads, d_head), x.shape
```

- 变量命名带上形状提示：`resid_BPD`，或者在注释里写 `# [batch, pos, d_model]`。
- 写完先用 `batch=2, pos=3` 这种**互不相同**的小尺寸跑一遍，维度一旦写反会立刻报错（各维相等时反而发现不了）。
- 想要运行时检查，可以给 jaxtyping 配上 beartype / typeguard。
