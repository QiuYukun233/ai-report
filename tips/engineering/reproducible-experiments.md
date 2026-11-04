---
title: 让实验可复现：种子、配置、结果落盘
track: engineering
tags: [pytorch, python-tooling]
date: 2026-11-04
---

```python
import random, numpy as np, torch
def seed_all(s: int = 0):
    random.seed(s); np.random.seed(s); torch.manual_seed(s); torch.cuda.manual_seed_all(s)
```

- **依赖锁定**：用 `uv` 管理环境（`uv add transformer-lens`，然后提交 `uv.lock`）。
- **配置和代码分开**：超参数放在 dataclass 或 YAML 里，每次运行都把配置和 git commit hash 一起存进结果目录。
- **结果落盘**：`runs/2026-11-04_patching_ioi/{config.json, results.pt, fig.png}`；大文件不进 git（`.gitignore` 里已经排除了 `*.pt`）。
- **推理不要梯度**：`torch.inference_mode()` 比 `no_grad()` 更省资源；显存紧张时及时 `del cache` + `torch.cuda.empty_cache()`。
- GPU 上的完全确定性需要 `torch.use_deterministic_algorithms(True)`，会更慢，按需开启。
