"""A dependency-free reference for the three ways to execute a shared-state decision.

Standalone: this imports nothing from ai-radar and belongs in its own repository once
it outgrows an afternoon. It lives here so the work survives the container.

## What this is for

Every open System One implementation asks the same question — *one long state, many
short criteria* — and answers it with a different execution strategy. The strategies
are usually described as if they were different algorithms. They are not. They are
three different **visibility constructions over the same tokens**, and they must all
produce bit-identical logits. What differs is only what it costs to get them.

This file builds a two-layer toy transformer (RMSNorm, RoPE, single-head attention,
SwiGLU-ish MLP, residuals) in pure Python, expresses all three strategies as node
lists, and checks that they agree. Nothing here needs torch, a GPU, a tokenizer or a
pretrained checkpoint, which is the point: correctness and cost scaling are decidable
without any of that. Only accuracy and calibration need a real model.

## The three strategies

``independent``  Each criterion is its own sequence, ``[state ++ tail_i]``, encoded from
                 scratch under an ordinary causal mask. This is what NanoJev's trained
                 pipeline actually does — its timing report says so: no shared tree, no
                 KV prefix reuse.

``branched``     The state is encoded once and the resulting KV is *replicated* per
                 branch, which is SemIf's ``reorder_cache(zeros(N))`` on Torch and its
                 ``copy.deepcopy(cache)`` on MLX. Mathematically identical to
                 ``independent`` — every query sees exactly the same keys. The saving is
                 that the state's forward pass happens once; the cost is that N copies
                 of the state's KV are resident.

``packed``       One sequence ``[state ++ tail_1 ++ ... ++ tail_N]`` under a
                 block-diagonal mask: each tail sees the state and itself, never a
                 sibling. Positions restart at ``len(state)`` for every tail, so two
                 tails genuinely occupy the same position indices — which is correct,
                 because RoPE is relative and the blocks cannot see each other. The
                 state's KV is resident exactly once. This is Jev's actual architecture
                 and the one nobody has deployed.

Because all three are the same mathematics, ``check()`` asserts agreement to a tight
tolerance and then asserts that two deliberate mistakes — a plain global causal mask
over the packed sequence, and packed positions that run on instead of restarting — do
*not* agree. A test that cannot fail is not a test.

Run: python -m decisionbench.reference
"""

from __future__ import annotations

import json
import math
import random

DIM = 8
LAYERS = 2
RNG = random.Random(1729)


# ---------------------------------------------------------------------------
# A toy transformer, written out longhand so every step is inspectable
# ---------------------------------------------------------------------------

def _matrix() -> list[list[float]]:
    return [[RNG.uniform(-0.5, 0.5) for _ in range(DIM)] for _ in range(DIM)]


PARAMS = [{name: _matrix() for name in ("q", "k", "v", "o", "f1", "f2")}
          for _ in range(LAYERS)]
READOUT = [[RNG.uniform(-0.5, 0.5) for _ in range(DIM)] for _ in range(4)]


def _dot(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def _linear(x: list[float], w: list[list[float]]) -> list[float]:
    return [_dot(row, x) for row in w]


def _rmsnorm(x: list[float]) -> list[float]:
    scale = math.sqrt(sum(v * v for v in x) / len(x) + 1e-6)
    return [v / scale for v in x]


def _rope(x: list[float], position: int) -> list[float]:
    """Rotary embedding. Note it depends only on ``position``, never on array index —
    which is exactly why two packed branches may share position numbers."""
    out = []
    for i in range(0, DIM, 2):
        angle = position / (10000 ** (i / DIM))
        cos, sin = math.cos(angle), math.sin(angle)
        out.extend([x[i] * cos - x[i + 1] * sin, x[i] * sin + x[i + 1] * cos])
    return out


def _softmax(values: list[float]) -> list[float]:
    top = max(values)
    weights = [math.exp(v - top) for v in values]
    total = sum(weights)
    return [w / total for w in weights]


def _embed(token: int) -> list[float]:
    return [math.sin(token * (i + 1) * 0.37) for i in range(DIM)]


def run(nodes: list[dict]) -> list[list[float]]:
    """Forward the toy model over ``nodes``.

    Each node is ``{"token": int, "pos": int, "visible": [indices]}``. The visibility
    list is the entire difference between the three strategies — nothing else in this
    function knows which one is being executed.
    """
    hidden = [_embed(node["token"]) for node in nodes]
    for layer in PARAMS:
        normed = [_rmsnorm(h) for h in hidden]
        queries = [_rope(_linear(h, layer["q"]), n["pos"]) for h, n in zip(normed, nodes)]
        keys = [_rope(_linear(h, layer["k"]), n["pos"]) for h, n in zip(normed, nodes)]
        values = [_linear(h, layer["v"]) for h in normed]
        updated = []
        for index, node in enumerate(nodes):
            visible = node["visible"]
            weights = _softmax([_dot(queries[index], keys[j]) / math.sqrt(DIM)
                                for j in visible])
            attended = [sum(w * values[j][d] for w, j in zip(weights, visible))
                        for d in range(DIM)]
            residual = [a + b for a, b in zip(hidden[index], _linear(attended, layer["o"]))]
            gate = _linear(_rmsnorm(residual), layer["f1"])
            gate = [g / (1 + math.exp(-g)) for g in gate]
            updated.append([a + b for a, b in zip(residual, _linear(gate, layer["f2"]))])
        hidden = updated
    return hidden


def decide(hidden_state: list[float], options: int) -> list[float]:
    """The readout: project the final hidden state, keep one row per option, softmax."""
    return _softmax([_dot(READOUT[i], hidden_state) for i in range(options)])


# ---------------------------------------------------------------------------
# The three visibility constructions
# ---------------------------------------------------------------------------

def _causal(nodes: list[dict], start: int, prefix: list[int]) -> None:
    """Give each node from ``start`` onward sight of ``prefix`` plus its own history."""
    for offset in range(start, len(nodes)):
        nodes[offset]["visible"] = prefix + list(range(start, offset + 1))


def independent(state: list[int], tails: list[list[int]]) -> list[list[dict]]:
    """One full sequence per criterion. No sharing of any kind."""
    sequences = []
    for tail in tails:
        nodes = [{"token": t, "pos": i, "visible": list(range(i + 1))}
                 for i, t in enumerate(state)]
        for offset, token in enumerate(tail):
            index = len(state) + offset
            nodes.append({"token": token, "pos": index,
                          "visible": list(range(index + 1))})
        sequences.append(nodes)
    return sequences


def packed(state: list[int], tails: list[list[int]], *,
           wrong_mask: bool = False, wrong_positions: bool = False) -> list[dict]:
    """One sequence, block-diagonal mask, positions restarting per tail.

    ``wrong_mask`` applies an ordinary global causal mask instead, so later tails can
    see earlier ones — the single most likely bug in a hand-built packed implementation,
    and one that produces plausible output rather than a crash.

    ``wrong_positions`` lets positions run on through the packed sequence instead of
    restarting at ``len(state)`` for each tail. Also silent, also wrong.
    """
    nodes = [{"token": t, "pos": i, "visible": list(range(i + 1))}
             for i, t in enumerate(state)]
    state_indices = list(range(len(state)))
    running = len(state)
    for tail in tails:
        start = len(nodes)
        for offset, token in enumerate(tail):
            index = len(nodes)
            position = running + offset if wrong_positions else len(state) + offset
            visible = (list(range(index + 1)) if wrong_mask
                       else state_indices + list(range(start, index + 1)))
            nodes.append({"token": token, "pos": position, "visible": visible})
        running += len(tail)
    return nodes


# ---------------------------------------------------------------------------
# Cost, counted rather than benchmarked
# ---------------------------------------------------------------------------

def costs(state_len: int, tail_lens: list[int]) -> dict:
    """Resident KV vectors and query-key products for each strategy.

    The point of counting rather than timing: the asymptotic difference between the
    strategies is exact and hardware-independent, so it can be established on a laptop
    and only *confirmed* on a rented GPU.
    """
    n = len(tail_lens)
    total_tail = sum(tail_lens)

    def pairs(prefix: int, tail: int) -> int:
        # tokens inside the tail attend to the prefix plus their own left context
        return sum(prefix + k + 1 for k in range(tail))

    independent_pairs = sum(
        sum(k + 1 for k in range(state_len)) + pairs(state_len, t) for t in tail_lens)
    shared_pairs = sum(k + 1 for k in range(state_len)) + sum(
        pairs(state_len, t) for t in tail_lens)
    return {
        "independent": {"kv": sum(state_len + t for t in tail_lens),
                        "qk_pairs": independent_pairs,
                        "state_encoded_times": n},
        "branched": {"kv": sum(state_len + t for t in tail_lens),
                     "qk_pairs": shared_pairs,
                     "state_encoded_times": 1},
        "packed": {"kv": state_len + total_tail,
                   "qk_pairs": shared_pairs,
                   "state_encoded_times": 1},
    }


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------

STATE = [11, 12, 13, 14, 15, 16, 17]
TAILS = [[21, 22, 23], [31, 32], [41, 42, 43, 44]]
OPTIONS = [3, 2, 4]


def _packed_answers(nodes: list[dict], tails: list[list[int]], state_len: int,
                    options: list[int]) -> list[list[float]]:
    hidden = run(nodes)
    answers, cursor = [], state_len
    for tail, k in zip(tails, options):
        cursor += len(tail)
        answers.append(decide(hidden[cursor - 1], k))
    return answers


def _independent_answers(state: list[int], tails: list[list[int]],
                         options: list[int]) -> list[list[float]]:
    return [decide(run(nodes)[-1], k)
            for nodes, k in zip(independent(state, tails), options)]


def _max_gap(a: list[list[float]], b: list[list[float]]) -> float:
    return max(abs(x - y) for pa, pb in zip(a, b) for x, y in zip(pa, pb))


def check() -> dict:
    reference = _independent_answers(STATE, TAILS, OPTIONS)
    agree = _max_gap(reference, _packed_answers(
        packed(STATE, TAILS), TAILS, len(STATE), OPTIONS))
    bad_mask = _max_gap(reference, _packed_answers(
        packed(STATE, TAILS, wrong_mask=True), TAILS, len(STATE), OPTIONS))
    bad_positions = _max_gap(reference, _packed_answers(
        packed(STATE, TAILS, wrong_positions=True), TAILS, len(STATE), OPTIONS))

    # Changing one tail must not move any other tail's answer: that is what branch
    # isolation means, and it is the property the block-diagonal mask exists to provide.
    altered = [TAILS[0], [99, 98], TAILS[2]]
    neighbours = _packed_answers(packed(STATE, altered), altered, len(STATE), OPTIONS)
    leak = max(_max_gap([reference[0]], [neighbours[0]]),
               _max_gap([reference[2]], [neighbours[2]]))
    moved = _max_gap([reference[1]], [neighbours[1]])

    return {
        "packed_vs_independent": agree,
        "negative_control_global_causal_mask": bad_mask,
        "negative_control_running_positions": bad_positions,
        "sibling_leak_when_one_tail_changes": leak,
        "changed_tail_actually_moved": moved,
        "costs": costs(len(STATE), [len(t) for t in TAILS]),
    }


def main() -> int:
    result = check()
    print(json.dumps({k: v for k, v in result.items() if k != "costs"}, indent=2))

    assert result["packed_vs_independent"] < 1e-9, "packed must match independent"
    assert result["negative_control_global_causal_mask"] > 1e-6, "bad mask went undetected"
    assert result["negative_control_running_positions"] > 1e-6, "bad positions undetected"
    assert result["sibling_leak_when_one_tail_changes"] < 1e-12, "branches are not isolated"
    assert result["changed_tail_actually_moved"] > 1e-6, "the perturbation did nothing"

    # independent and branched hold the same KV; they differ only in how many times the
    # state is *encoded*. Packing is the only one of the three that changes the memory.
    print("\none 2000-token state, 20-token criteria:")
    print(f"{'criteria':>9} {'state encodes':>14} {'KV indep/branched':>19} "
          f"{'KV packed':>11} {'packing saves':>14}")
    for n in (1, 4, 16, 64, 256):
        c = costs(2000, [20] * n)
        print(f"{n:>9} {c['independent']['state_encoded_times']:>6} vs {1:<5} "
              f"{c['branched']['kv']:>19,} {c['packed']['kv']:>11,} "
              f"{c['branched']['kv'] / c['packed']['kv']:>13.1f}x")
    print("\nAll checks passed, including both negative controls.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
