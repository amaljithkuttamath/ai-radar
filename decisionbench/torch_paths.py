"""The three execution strategies on a real transformer, checked and measured.

``reference.py`` establishes that independent, branched and packed execution are the
same mathematics. This file implements all three against an actual HuggingFace causal
model and answers the question the open ecosystem has not: **what does packing buy at
realistic state lengths?** Every published System One number — SemIf, sarvam-jev,
NanoJev — is measured at 85 input tokens or fewer, where there is nothing to amortise.

Runs on CPU against a tiny random config for development (no checkpoint, no tokenizer,
no network), and unchanged on a GPU against a real one:

    python -m decisionbench.torch_paths                       # tiny random, CPU
    python -m decisionbench.torch_paths --model google/medgemma-4b-pt --dtype bf16

## The negative controls are the point

HuggingFace's mask plumbing can silently ignore a custom 4D mask and substitute its own
packed causal mask — NanoJev's architecture audit flags exactly this: *"Transformers may
pass None, silently dropping the constraint."* A packed implementation whose mask is
being ignored still returns plausible probabilities. It is wrong in a way no assertion
about output *shape* can catch.

So ``verify`` asserts two things, and the second matters more than the first:

1. packed agrees with independent (tight tolerance in fp32), and
2. a deliberately global-causal mask and deliberately running positions **disagree**.

If (2) ever passes silently, the mask is not reaching the attention kernel and (1) was
meaningless.
"""

from __future__ import annotations

import argparse
import json
import time

import torch

NEG_CONTROL_MIN = 1e-4


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------

def load(model_id: str = "", dtype: str = "fp32", device: str = ""):
    """A real checkpoint when named, otherwise a tiny random one built offline."""
    from transformers import AutoModel, LlamaConfig, LlamaModel

    torch_dtype = {"fp32": torch.float32, "fp16": torch.float16,
                   "bf16": torch.bfloat16}[dtype]
    device = device or ("cuda:0" if torch.cuda.is_available() else "cpu")
    if model_id:
        model = AutoModel.from_pretrained(model_id, dtype=torch_dtype).to(device)
    else:
        torch.manual_seed(1729)
        config = LlamaConfig(hidden_size=128, num_hidden_layers=4, num_attention_heads=8,
                             num_key_value_heads=4, intermediate_size=256,
                             vocab_size=512, max_position_embeddings=65536)
        model = LlamaModel(config).to(device=device, dtype=torch_dtype)
    return model.eval(), device, torch_dtype


def kv_bytes(model, tokens: int, torch_dtype) -> int:
    """Analytic resident KV size — the number a CPU run cannot measure but can compute."""
    config = model.config
    heads = getattr(config, "num_key_value_heads", config.num_attention_heads)
    head_dim = getattr(config, "head_dim", config.hidden_size // config.num_attention_heads)
    element = torch.finfo(torch_dtype).bits // 8
    return 2 * config.num_hidden_layers * heads * head_dim * tokens * element


# ---------------------------------------------------------------------------
# The three paths. Each returns one hidden vector per criterion.
# ---------------------------------------------------------------------------

def _mask_from_visibility(visible: torch.Tensor, torch_dtype) -> torch.Tensor:
    """Boolean visibility -> additive mask. Uses dtype min, never -inf: a fully masked
    row would make -inf produce NaN through softmax rather than a usable zero row."""
    mask = torch.zeros(visible.shape, dtype=torch_dtype, device=visible.device)
    return mask.masked_fill_(~visible, torch.finfo(torch_dtype).min)[None, None]


@torch.inference_mode()
def run_independent(model, state, tails, device):
    """One full sequence per criterion, batched and right-padded. No reuse at all."""
    lengths = [len(state) + len(t) for t in tails]
    width = max(lengths)
    ids = torch.zeros(len(tails), width, dtype=torch.long, device=device)
    attn = torch.zeros(len(tails), width, dtype=torch.long, device=device)
    for i, tail in enumerate(tails):
        row = state + tail
        ids[i, :len(row)] = torch.tensor(row, device=device)
        attn[i, :len(row)] = 1
    out = model(input_ids=ids, attention_mask=attn).last_hidden_state
    return torch.stack([out[i, lengths[i] - 1] for i in range(len(tails))])


@torch.inference_mode()
def run_branched(model, state, tails, device):
    """Prefill the state once, replicate its KV per branch, run the tails together.

    This is SemIf's Torch path. The replication is a beam-search primitive: indexing a
    batch of one with [0,0,...,0] broadcasts the single prefill across N branches.
    """
    prefix = torch.tensor([state], dtype=torch.long, device=device)
    prefilled = model(input_ids=prefix,
                      attention_mask=torch.ones_like(prefix), use_cache=True)
    cache = prefilled.past_key_values
    cache.reorder_cache(torch.zeros(len(tails), dtype=torch.long, device=device))

    width = max(len(t) for t in tails)
    ids = torch.zeros(len(tails), width, dtype=torch.long, device=device)
    attn = torch.zeros(len(tails), len(state) + width, dtype=torch.long, device=device)
    pos = torch.zeros(len(tails), width, dtype=torch.long, device=device)
    for i, tail in enumerate(tails):
        ids[i, :len(tail)] = torch.tensor(tail, device=device)
        attn[i, :len(state) + len(tail)] = 1
        pos[i, :len(tail)] = torch.arange(len(state), len(state) + len(tail), device=device)
    out = model(input_ids=ids, attention_mask=attn, position_ids=pos,
                past_key_values=cache, use_cache=True).last_hidden_state
    return torch.stack([out[i, len(tails[i]) - 1] for i in range(len(tails))])


@torch.inference_mode()
def run_packed(model, state, tails, device, torch_dtype, *,
               wrong_mask: bool = False, wrong_positions: bool = False):
    """One sequence, block-diagonal mask, positions restarting at len(state) per tail.

    Two tails deliberately occupy the same position indices. That is correct: RoPE is
    relative, and the mask guarantees the blocks never see one another.
    """
    flat = list(state)
    spans = []
    for tail in tails:
        spans.append((len(flat), len(flat) + len(tail)))
        flat.extend(tail)
    total = len(flat)

    ids = torch.tensor([flat], dtype=torch.long, device=device)
    positions = list(range(len(state)))
    causal = torch.ones(total, total, dtype=torch.bool, device=device).tril()
    visible = causal.clone() if wrong_mask else torch.zeros_like(causal)
    if not wrong_mask:
        visible[: len(state), : len(state)] = causal[: len(state), : len(state)]
    running = len(state)
    for start, end in spans:
        length = end - start
        positions.extend(range(running, running + length) if wrong_positions
                         else range(len(state), len(state) + length))
        running += length
        if not wrong_mask:
            visible[start:end, : len(state)] = True          # sees the state
            visible[start:end, start:end] = causal[start:end, start:end]  # and itself

    out = model(input_ids=ids,
                attention_mask=_mask_from_visibility(visible, torch_dtype),
                position_ids=torch.tensor([positions], dtype=torch.long, device=device),
                ).last_hidden_state
    return torch.stack([out[0, end - 1] for _, end in spans])


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------

def _gap(a: torch.Tensor, b: torch.Tensor) -> float:
    return float((a.float() - b.float()).abs().max())


def verify(model, device, torch_dtype, state_len: int = 96,
           tail_lens=(12, 7, 19, 5)) -> dict:
    vocab = model.config.vocab_size
    generator = torch.Generator().manual_seed(7)
    pick = lambda n: torch.randint(1, vocab, (n,), generator=generator).tolist()
    state = pick(state_len)
    tails = [pick(n) for n in tail_lens]

    independent = run_independent(model, state, tails, device)
    branched = run_branched(model, state, tails, device)
    packed = run_packed(model, state, tails, device, torch_dtype)
    bad_mask = run_packed(model, state, tails, device, torch_dtype, wrong_mask=True)
    bad_pos = run_packed(model, state, tails, device, torch_dtype, wrong_positions=True)

    report = {
        "dtype": str(torch_dtype).replace("torch.", ""),
        "branched_vs_independent": _gap(branched, independent),
        "packed_vs_independent": _gap(packed, independent),
        "negative_control_global_causal_mask": _gap(bad_mask, independent),
        "negative_control_running_positions": _gap(bad_pos, independent),
    }
    report["mask_reached_the_kernel"] = (
        report["negative_control_global_causal_mask"] > NEG_CONTROL_MIN)
    report["positions_reached_the_kernel"] = (
        report["negative_control_running_positions"] > NEG_CONTROL_MIN)
    return report


# ---------------------------------------------------------------------------
# Measurement
# ---------------------------------------------------------------------------

def measure(model, device, torch_dtype, state_len: int, criteria: int,
            tail_len: int = 20, repeats: int = 3) -> dict:
    vocab = model.config.vocab_size
    generator = torch.Generator().manual_seed(11)
    state = torch.randint(1, vocab, (state_len,), generator=generator).tolist()
    tails = [torch.randint(1, vocab, (tail_len,), generator=generator).tolist()
             for _ in range(criteria)]

    def timed(fn) -> tuple[float, int]:
        sync = (lambda: torch.cuda.synchronize(device)) if device.startswith("cuda") else (lambda: None)
        if device.startswith("cuda"):
            torch.cuda.reset_peak_memory_stats(device)
        fn(); sync()                                    # warm up, then measure
        best = float("inf")
        for _ in range(repeats):
            sync(); mark = time.perf_counter(); fn(); sync()
            best = min(best, time.perf_counter() - mark)
        peak = torch.cuda.max_memory_allocated(device) if device.startswith("cuda") else 0
        return best, peak

    results = {"state_len": state_len, "criteria": criteria, "tail_len": tail_len}
    for name, fn in (
        ("independent", lambda: run_independent(model, state, tails, device)),
        ("branched", lambda: run_branched(model, state, tails, device)),
        ("packed", lambda: run_packed(model, state, tails, device, torch_dtype)),
    ):
        seconds, peak = timed(fn)
        results[name] = {"seconds": round(seconds, 5), "peak_gpu_bytes": peak}
    # What a CPU run cannot measure but can compute exactly.
    results["kv_bytes_resident"] = {
        "branched": kv_bytes(model, criteria * (state_len + tail_len), torch_dtype),
        "packed": kv_bytes(model, state_len + criteria * tail_len, torch_dtype),
    }
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default="", help="HF id; omit for a tiny random model")
    parser.add_argument("--dtype", default="fp32", choices=("fp32", "fp16", "bf16"))
    parser.add_argument("--device", default="")
    parser.add_argument("--sweep", default="256,1024,4096",
                        help="comma-separated state lengths to measure")
    parser.add_argument("--criteria", default="1,4,16",
                        help="comma-separated criterion counts to measure")
    args = parser.parse_args()

    model, device, torch_dtype = load(args.model, args.dtype, args.device)
    print(f"device={device} dtype={args.dtype} "
          f"model={args.model or 'tiny-random-llama'}\n")

    report = verify(model, device, torch_dtype)
    print(json.dumps(report, indent=2))
    assert report["mask_reached_the_kernel"], (
        "the block-diagonal mask was silently ignored — a global causal mask gave the "
        "same answer, so every equivalence number above is meaningless")
    assert report["positions_reached_the_kernel"], "position_ids were silently ignored"
    tolerance = 1e-4 if torch_dtype == torch.float32 else 5e-2
    assert report["packed_vs_independent"] < tolerance, "packed does not match independent"
    assert report["branched_vs_independent"] < tolerance, "branched does not match independent"

    print(f"\n{'state':>7} {'crit':>5} {'independent':>12} {'branched':>10} {'packed':>10} "
          f"{'KV branched':>13} {'KV packed':>11} {'saves':>7}")
    rows = []
    for state_len in [int(v) for v in args.sweep.split(",")]:
        for criteria in [int(v) for v in args.criteria.split(",")]:
            row = measure(model, device, torch_dtype, state_len, criteria)
            rows.append(row)
            kv = row["kv_bytes_resident"]
            print(f"{state_len:>7} {criteria:>5} {row['independent']['seconds']:>12.4f} "
                  f"{row['branched']['seconds']:>10.4f} {row['packed']['seconds']:>10.4f} "
                  f"{kv['branched'] / 1e6:>12.1f}M {kv['packed'] / 1e6:>10.1f}M "
                  f"{kv['branched'] / kv['packed']:>6.1f}x")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
