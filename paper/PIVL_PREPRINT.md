# PIVL: Persistent Instruction Verification Loops for Reducing Instruction Drift in Long-Horizon LLM Agents

**Mohideen Fasith Ahamed**  
Independent Researcher  
Preprint / System Proposal — September 2026

## Abstract

Large language model (LLM) agents increasingly operate over long conversations, policy files, project instructions, and tool-use trajectories. A practical failure mode is **instruction drift**: a standing requirement stated earlier remains nominally available but is no longer reliably enforced when the agent later proposes or executes an action. We propose **PIVL (Persistent Instruction Verification Loop)**, a model-agnostic control layer that separates standing instructions and observed failures from ordinary conversational context. PIVL stores rules in persistent external state, routes relevant rules before each action, compiles objectively testable rules into deterministic predicates, gates actions through pre- and post-action verification, records violations, and derives persistent prevention checks from failures. A working v0.1 prototype uses SQLite-backed state, a deterministic rule compiler, an instruction router, and a fail-closed semantic-verifier interface. Engineering tests show that the gate correctly blocks invalid submissions across a 200-turn synthetic horizon and permits the final action once all required predicates are satisfied. These results validate the mechanism, not the broader research hypothesis. We therefore define a falsifiable real-model A/B evaluation protocol comparing identical base models with and without PIVL.

**Keywords:** large language models, agents, instruction following, long context, verification, memory, reliability, context rot

## 1. Introduction

Long context windows can contain more information without guaranteeing uniform use of every earlier instruction. Prior work on long-context language models has shown positional degradation such as the “lost in the middle” effect. More recent benchmarks evaluate whether models continue obeying standing instructions across long multi-turn interactions and tool-use trajectories.

PIVL treats this as a runtime reliability problem. Conversational context is used as working memory, while binding constraints are stored in a persistent control state and re-checked at action boundaries.

The proposed contribution is intentionally narrow. Persistent memory, retrieval, rule engines, verifier models, and self-correction all have prior art. PIVL tests whether **persistent failure-derived constraints plus pre/post action gating** reduce repeated instruction violations over long task horizons without unacceptable false blocking, latency, or token overhead.

## 2. Problem definition

At turn *t*, let:

- **H_t**: conversational/task history;
- **a_t**: proposed agent action;
- **R_t**: active standing rules;
- **F_t**: observed failures;
- **P_t**: failure-derived prevention rules;
- **S_t**: externally observed task state.

A baseline conversational agent relies on the model to infer applicable constraints from **H_t**. PIVL maintains **M_t = (R_t, F_t, P_t)** outside ordinary context and evaluates actions before execution.

A router selects potentially applicable rules:

**R*_t = Route(a_t, S_t, R_t, F_t, P_t).**

For critical rules, the action gate is:

**Gate(a_t) = 1 iff every applicable critical rule passes.**

When a rule fails, PIVL records the failure event and creates or reinforces a prevention rule associated with that rule-action pair.

## 3. Architecture

### 3.1 Persistent rule registry

Standing instructions are stored as structured rules with an identifier, natural-language text, priority, scope, phase, active status, check type, configuration, provenance, and optional supersession information.

### 3.2 Deterministic rule compiler

Rules that can be objectively checked should be compiled into predicates rather than delegated to another LLM. PIVL v0.1 supports instructions such as:

```text
oracle_score must equal 1
artifact_path must exist
secret_file must not exist
before submit, nop_score must equal 0
never delete_production
```

Unknown instructions become semantic rules and require an external verifier.

### 3.3 Instruction router

Repeating every instruction before every turn can itself create context noise. The router therefore prioritizes rules relevant to the proposed action, scope, priority, and previous failure history, while keeping the full canonical rule set persistent.

### 3.4 Pre-action verification

Before execution, PIVL checks applicable constraints. If a required predicate fails, the action is blocked and the system returns the unmet conditions.

### 3.5 Post-action verification

PIVL can verify resulting external state after execution rather than trusting the model’s claim that it complied.

### 3.6 Failure memory and prevention rules

Each failed verification is stored persistently. PIVL derives a prevention rule such as: “Before `submit`, re-check rule R17.” The base rule remains the source of truth; the prevention rule increases future attention to a previously violated constraint.

### 3.7 Semantic verifier interface

Instructions that cannot be reduced to deterministic predicates can be checked through a constrained semantic-verifier adapter. Production systems should measure false-pass and false-block rates for this component independently.

## 4. Prototype implementation

PIVL v0.1 includes:

- SQLite-backed rule and failure storage;
- deterministic rule compiler;
- action-specific routing;
- pre- and post-action verification;
- failure-derived prevention rules;
- semantic-verifier extension point;
- unit tests;
- synthetic 200-turn benchmark;
- interactive browser demonstration.

The implementation is model-agnostic and does not require an API key for the engineering demo.

## 5. Engineering validation

The current evidence validates the control mechanism only.

| Test | Result |
|---|---|
| Unit tests | 3/3 passed |
| Submission with Oracle and NOP missing | Blocked |
| Submission after NOP=0 but Oracle missing | Blocked |
| Submission after Oracle=1 and NOP=0 | Allowed |
| Synthetic horizon | 200 turns |
| Early invalid submissions proposed | 5 |
| Early invalid submissions blocked | 5/5 |
| Final valid submission | Allowed |
| Failure records in synthetic run | 10 |
| Failure-derived prevention rules | 2 |

These results do **not** prove that PIVL improves GPT, Claude, Gemini, or any other real model.

## 6. Proposed real-model evaluation

Compare identical base models in two conditions:

- **Baseline:** ordinary conversational context and tool access.
- **PIVL:** same model and tools plus persistent rule/failure state and action gating.

Vary:

- horizon length: 25, 50, 100, 200 turns;
- standing-rule count;
- rule position: early, middle, recent;
- deterministic vs. semantic constraints;
- rule updates, exceptions, and supersession;
- distractor density;
- reversible vs. irreversible actions;
- repeated opportunities to make the same earlier mistake.

Primary metrics:

- instruction compliance rate;
- repeated-failure rate;
- critical violation rate;
- strict task success rate;
- false-pass rate;
- false-block rate;
- recovery after failure;
- token overhead;
- latency and model-inference cost.

### Ablation plan

Evaluate progressively:

1. persistent rules only;
2. + routing;
3. + pre-action gate;
4. + post-action verification;
5. + failure memory;
6. + failure-derived prevention rules (full PIVL).

If the failure-derived component does not provide an incremental improvement in repeated-failure rate, that part of the hypothesis should be rejected or revised.

## 7. Limitations

The deterministic compiler currently supports a narrow grammar. Real instructions may be conditional, temporal, scoped, ambiguous, or conflicting. Failure-derived rules in v0.1 are persistent reminders rather than learned policies. The synthetic benchmark does not measure real-model behavior. Semantic verifier models can themselves hallucinate or drift. Persistent memory also requires governance for rule provenance, retention, privacy, supersession, and deletion.

PIVL should therefore be presented as a **research hypothesis and working prototype**, not as a solved context-rot problem.

## 8. Safety and governance

Production systems should authenticate rule provenance, separate system and user policy layers, maintain version history, define explicit precedence, protect stored failure information, and apply stronger checks to high-impact or irreversible actions.

## 9. Research roadmap

**v0.2:** rule versioning, conflict resolution, provenance, semantic-verifier adapters, structured evidence, and risk-weighted gates.

**v0.3:** automatic instruction extraction, learned routing, adversarial instruction-drift benchmarks, and multi-model reproducible evaluation.

**Research milestone:** preregistered A/B testing showing whether PIVL produces a statistically significant reduction in repeated violations at acceptable cost and false-block rates.

## 10. Conclusion

Long-running LLM agents can fail even when the original instruction is technically still present in their history. PIVL reframes this as a runtime control problem: persist binding rules, surface relevant constraints at action time, verify objective requirements programmatically, check resulting state, and turn observed violations into future prevention checks.

The v0.1 prototype shows that this mechanism is implementable and can enforce deterministic standing constraints across a synthetic long horizon. The central scientific question remains open: whether it materially improves real model agents under realistic workloads. The proposed evaluation protocol is designed to make that question testable and falsifiable.

## Acknowledgment

The prototype implementation and manuscript preparation used AI-assisted coding and drafting. The author remains responsible for the claims, experimental design, interpretation, and any future submission.

## References

1. N. F. Liu, K. Lin, J. Hewitt, A. Paranjape, M. Bevilacqua, F. Petroni, and P. Liang. “Lost in the Middle: How Language Models Use Long Contexts.” *Transactions of the Association for Computational Linguistics*, 12:157–173, 2024. DOI: 10.1162/tacl_a_00638.
2. P. K. Robinette, A. Hard, S. Ramaswamy, E. Amid, R. Mathews, and T. T. Johnson. “We Are What We Repeatedly Do: Improving Long Context Instruction Following.” *Findings of EACL 2026*, 2026. DOI: 10.18653/v1/2026.findings-eacl.254.
3. Q. Jia, Y. Shen, X. Song, K. Zhang, S. Wang, D. Pei, X. Zhu, and G. Zhai. “One Battle After Another: Probing LLMs’ Limits on Multi-Turn Instruction Following with a Benchmark Evolving Framework.” *ACL 2026*, 2026. DOI: 10.18653/v1/2026.acl-long.433.
4. L. Panavas, S. Minus, B. Monton, D. Ray, S. Garre, S. Mehta, and E. Chen. “HANDBOOK.md: A Benchmark for Long-Context Agentic Instruction Following.” arXiv:2607.25398, 2026.
5. A. L. Zhang, T. Kraska, and O. Khattab. “Recursive Language Models.” arXiv:2512.24601, 2025.
