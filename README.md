# PIVL v0.1 — Persistent Instruction Verification Loop

PIVL is a research prototype for reducing instruction drift in long-running AI tasks. Instead of trusting a language model to keep every old instruction active in its working context, PIVL stores instructions and failures in persistent external state and gates important actions through explicit verification.

## Live research demo

- Interactive prototype: https://raw.githack.com/Fasithahamed12/fasith-ahamed12/main/index.html
- Research preprint: [paper/PIVL_PREPRINT.md](paper/PIVL_PREPRINT.md)
- Source repository: https://github.com/Fasithahamed12/fasith-ahamed12

The public browser demo is a deterministic visualization of the PIVL action gate; it is not a claim of real-model performance improvement.

## Core hypothesis

> Long-horizon agent reliability can improve when standing instructions and prior violations are maintained outside conversational context, relevant rules are retrieved before each action, and actions are blocked until applicable constraints pass verification.

PIVL also converts detected failures into persistent **prevention rules**, so the system explicitly remembers which checks previously failed.

## Architecture

```text
Instructions
    ↓
Rule Compiler ──────────────┐
    ↓                       │
Persistent Rule Registry    │
    ↓                       │
Instruction Router          │
    ↓                       │
Proposed Action             │
    ↓                       │
Pre-action Verifier ──fail──┤→ Failure Memory → Prevention Rule
    ↓ pass                  │
Executor                    │
    ↓                       │
Post-action Verifier ─fail──┘
    ↓
Continue
```

## What v0.1 includes

- SQLite-backed persistent rule registry
- SQLite-backed failure memory
- Narrow deterministic natural-language rule compiler
- Relevance router that prioritizes action-specific and previously failed rules
- Pre-action and post-action verification
- Failure-derived prevention rules
- Fail-closed handling for semantic rules unless a semantic verifier is supplied
- Synthetic long-horizon harness
- Unit tests

## Engineering validation

- Unit tests: **3/3 passed**
- Synthetic horizon: **200 turns**
- Early invalid submissions proposed: **5**
- Early invalid submissions blocked: **5/5**
- Final valid submission: **allowed**
- Failure records in synthetic run: **10**
- Failure-derived prevention rules: **2**

These results validate the mechanism only. A publishable result requires controlled real-model A/B tests.

## License

MIT
