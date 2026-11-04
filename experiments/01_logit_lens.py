"""Logit lens on GPT-2 small：逐层看目标 token 的 logit 和排名。

    uv pip install transformer-lens   # 或 pip install transformer-lens
    python experiments/01_logit_lens.py --prompt "The Eiffel Tower is in the city of" --target " Paris"

CPU 上运行即可（gpt2-small 约 500MB，首次运行会下载）。
"""
import argparse

import torch
from transformer_lens import HookedTransformer


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="gpt2-small")
    ap.add_argument("--prompt", default="The Eiffel Tower is in the city of")
    ap.add_argument("--target", default=" Paris")
    args = ap.parse_args()

    model = HookedTransformer.from_pretrained(args.model)
    target = model.to_single_token(args.target)
    print("tokens:", model.to_str_tokens(args.prompt))

    with torch.inference_mode():
        _, cache = model.run_with_cache(args.prompt)
        resid, labels = cache.accumulated_resid(layer=-1, incl_mid=False, pos_slice=-1, return_labels=True)
        resid = cache.apply_ln_to_stack(resid, layer=-1, pos_slice=-1)
        logits = resid @ model.W_U + model.b_U          # [n_layers+1, batch, d_vocab]

    print(f"\n{'layer':<14}{'logit':>8}{'rank':>8}  top-1")
    for label, lg in zip(labels, logits[:, 0]):
        rank = int((lg > lg[target]).sum())
        top = model.to_string(lg.argmax())
        print(f"{label:<14}{lg[target].item():>8.2f}{rank:>8}  {top!r}")


if __name__ == "__main__":
    main()
