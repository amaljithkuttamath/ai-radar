# ADR-0008. NVIDIA joins the recognised model families

**Status.** Accepted, 2026-08. Extends ADR-0007; does not weaken the fence it added.

## Context

The separation fence (`grader/separation.py`, ADR-0007) refuses to run when it cannot prove the grader and synthesis models are different families.
Its family vocabulary is `llm.py:_FAMILY_HINTS`, and it is deliberately conservative: an unrecognised model id is refused, not assumed safe.
The fence's own error message names the remedy for a missing family: "Add it to `llm.py:_FAMILY_HINTS`."

Configuring the pipeline against OpenRouter's free tier exposed a gap in that vocabulary.
Of the free text-generation models the catalogue serves, the ones that respond most reliably are NVIDIA's Nemotron series (`nvidia/nemotron-3-ultra-550b-a55b:free` and siblings); the recognised-family free models (`gemma`, `gpt-oss`, `cohere`) were all rate-limited upstream at the time of writing.
`family()` returned `None` for every Nemotron id, even though Nemotron is a real, distinct training lineage that shares nothing with the `google`, `openai` or `cohere` families.

This bites on both sides of the fence, and the synthesis side is the one that actually blocked a run.
The pipeline synthesises the digest on Nemotron (it is the free model that responds), and the fence resolves the *synthesis* model's family too: an unrecognised synthesis model makes it refuse with "cannot prove the grader differs from it".
So without `nvidia` in the table, the fence cannot reason about a Nemotron-synthesized digest at all.
On the grader side the gap is real but secondary: recognising `nvidia` is necessary for a Nemotron grader to be considered, but not sufficient to make an all-free grader runnable, because that also needs a second un-throttled free family to pair against.

## Decision

**Add `nemotron` and `nvidia` to `_FAMILY_HINTS`, both mapping to family `nvidia`.**

This is a widening of the fence's *vocabulary*, not of its *logic*.
The rule is unchanged: two different recognised families pass, a shared family is refused, an unrecognised id is still refused.
Nemotron is now recognised the same way `claude`, `gemma` and `llama` are, so `nvidia/nemotron-*` resolves to `nvidia` in both the bare-id and gateway `vendor/model` forms.
A test asserts the pairing that motivated the change: a `nvidia` grader separates cleanly from a `google` synthesis model, exercised through the real `assert_separated` path rather than `family()` in isolation.

**Lineage is treated pragmatically, not as a graph.**
Some Nemotron variants are Llama-derived, so a strict "shared training lineage" reading could argue they collide with `meta`.
The family table has always been substring-pragmatic (`gemma` and `gemini` both map to `google` without modelling their actual relationship), and NVIDIA post-trains Nemotron heavily enough that treating it as its own family matches how the models behave and how the catalogue labels them.
Modelling derivation as a lineage graph would be gold-plating a table whose job is to keep a grader off its own output, not to be a taxonomy.

## Consequences

**Positive.**

- The fence can now reason about a Nemotron-synthesized digest instead of refusing it as unrecognised. This is what unblocked the pipeline: synthesis runs on `nvidia/nemotron-*`, and the fence resolves that family cleanly on both sides.
- The recognised-family vocabulary tracks the providers the pipeline actually runs against, which is the condition under which the fence stays useful rather than becoming a blanket refusal.
- A `nvidia` grader is now a legitimate candidate to pair against a non-`nvidia` synthesis model, which is one prerequisite for an all-free grader.

**Not yet true.**

- This does *not* make an all-free grader runnable. With synthesis pinned to `nvidia`, the grader must be a different family *and* actually respond, and the only free family responding right now is `nvidia`. `RADAR_GRADER_MODEL` is therefore deliberately left unset. The remaining blocker is upstream rate-limiting on the other free families, which no code change here touches.

**Negative.**

- The table grows by one family, and like every entry it is an assertion about model identity that a future provider rename could falsify. It is guarded by `test_family_detection`, not by anything that reads the provider's own metadata.
- Nemotron's partial Llama lineage means the `nvidia`/`meta` boundary is a judgement call, not a fact. If a future Nemotron is a thin Llama wrapper, grading it against a `meta` synthesis model would under-separate. This is accepted as the same pragmatism the rest of the table already runs on.

**Rejected.**

- *Widening the fence to pass unrecognised ids from "trusted" providers.* This is the exact failure mode ADR-0007 built the fence against. The remedy for an unknown model is to recognise it explicitly, which is what this ADR does, not to teach the fence to guess.
- *Mapping Nemotron to `meta` on lineage grounds.* Defensible in theory, but it would refuse a `nvidia`-grader / `meta`-synthesis pairing that is in practice a genuine cross-family check, and it overstates how much of Llama survives NVIDIA's post-training.
