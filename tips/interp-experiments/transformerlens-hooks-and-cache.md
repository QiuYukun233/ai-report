---
title: TransformerLens：用 run_with_cache 和 hooks 读写激活
track: interp
tags: [transformerlens, hooks]
date: 2026-11-04
source: https://transformerlensorg.github.io/TransformerLens/
---

**一句话**：`run_with_cache` 用来"读"激活，`run_with_hooks` 用来"改"激活。

```python
from transformer_lens import HookedTransformer
model = HookedTransformer.from_pretrained("gpt2-small")

logits, cache = model.run_with_cache("The Eiffel Tower is in")
resid = cache["resid_post", 5]          # 等价于 cache["blocks.5.hook_resid_post"]
attn  = cache["pattern", 3]             # [batch, head, q_pos, k_pos]

# 修改激活：把第 3 层 head 7 置零（zero-ablation）
def kill_head(z, hook, head=7):
    z[:, :, head, :] = 0                # hook_z 形状 [batch, pos, head, d_head]
    return z

ablated = model.run_with_hooks(
    "The Eiffel Tower is in",
    fwd_hooks=[("blocks.3.attn.hook_z", kill_head)],
)
```

**容易踩的坑**
- 只关心少数激活时用 `names_filter=lambda n: n.endswith("resid_post")`，能省大量显存。
- `model.to_str_tokens(prompt)` 先看清分词结果：GPT-2 的 token 往往带前导空格（`" Paris"` 和 `"Paris"` 是不同的 token）。
- 做大批量实验时套一层 `torch.inference_mode()`。
- `hook_z`、`hook_result`、`hook_attn_out` 是不同的位置，`model.hook_dict.keys()` 能列出所有 hook 点。
