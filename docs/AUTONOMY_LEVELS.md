# CCB Autonomy Levels (L1–L5)

CCB classifies every scenario by a **five-level model of AI autonomy**, adapted from
safety-critical autonomy taxonomies (SAE J3016 for autonomous vehicles, EASA/DO-178C for
aviation). Autonomy is treated as a *graded* property: each level is defined by how
decision-making authority is distributed between the human operator and the agent.

Each level carries a **Human Intervention Budget (HIB)** — the maximum number of points at
which the agent may request or require human input during a single scenario run. HIB turns
"level of autonomy" into a concrete, measurable constraint.

> **What is implemented today:** the released benchmark (ACE Bench) instantiates **L1 and L2
> only** — 40 scenarios across 8 CloudOps categories on AWS. **L3, L4, and L5 are defined by
> the framework but not yet implemented.** They require sandboxed execution, post-action state
> verification, and closed-loop infrastructure, and are reserved for follow-on work. See
> [Status & roadmap](#status--roadmap) below.

## The five levels

| Level | Name | Primary capability | HIB | Status |
|-------|------|--------------------|:---:|--------|
| **L1** | **Assistive** | Information retrieval and presentation; the human drives the workflow end-to-end. No independent analysis, no recommendations, no action on the environment. | ∞ | ✅ Implemented |
| **L2** | **Analytical** | Independent multi-step analysis over retrieved data → a structured assessment (patterns, aggregated findings, gaps/anomalies). Still does **not** recommend actions. | 4 | ✅ Implemented |
| **L3** | **Advisory** | Contextual **recommendations** with explicit tradeoff analysis across competing concerns (cost vs. resilience, security vs. performance). The agent reasons about the *right* remediation; the human still approves and executes. | 3 | 🔜 Defined, not yet implemented |
| **L4** | **Semi-Autonomous** | **Bounded execution**: the agent acts on the environment, but only within a sandbox/policy layer that enforces dry-run verification, rollback, and blast-radius limits. One human authorization per execution. | 1 | 🔜 Defined, not yet implemented |
| **L5** | **Autonomous** | **Closed-loop** goal-driven operation: observe → analyze → plan → execute → verify, with no human intervention within the scenario. A full realization of the MAPE-K autonomic control loop. | 0 | 🔜 Defined, not yet implemented |

*HIB = Human Intervention Budget (∞ = unbounded; 0 = none within the scenario).*

## What each level looks like in CloudOps

- **L1 — Assistive.** Answering targeted questions about a customer environment ("how many S3
  buckets have public access enabled?") or surfacing specific data points from provider APIs.
  Scored on correctness/completeness of retrieved information and output format.
- **L2 — Analytical.** A security-posture assessment across a set of resources, or identifying
  observability gaps. Scored on depth of analysis, grounding of findings in retrieved evidence,
  and fidelity of the reported assessment.
- **L3 — Advisory.** Producing a prioritized remediation roadmap, or recommending right-sizing
  changes for a compute fleet with cost/performance tradeoffs made explicit. Adds
  **reasoning-quality** scoring.
- **L4 — Semi-Autonomous.** Applying an approved remediation plan across a set of resources, or
  auto-remediating a well-characterized non-compliance within a defined scope. Adds scoring of
  **execution safety, action bounds, and outcome verification**.
- **L5 — Autonomous.** Sustained, goal-driven optimization of a customer environment against
  defined objectives, closed-loop. The human role is confined to setting the goal and reviewing
  outcomes.

## How autonomy level shapes scoring

The autonomy level determines not just expected behavior but the **dimensions** an agent is
scored on:

- **L1 / L2** — scored on retrieval and analysis dimensions (the four pillars used today:
  Answer, Fidelity, Safety, Output).
- **L3** — introduces **reasoning-quality** scoring (tradeoff analysis, remediation reasoning).
- **L4 / L5** — additionally require **execution-safety, action-bound, and outcome-verification**
  scoring, which can only be evaluated inside a sandbox that actually lets the agent act.

## Status & roadmap

| | L1 | L2 | L3 | L4 | L5 |
|---|:--:|:--:|:--:|:--:|:--:|
| Defined in framework | ✅ | ✅ | ✅ | ✅ | ✅ |
| Scenarios released | ✅ | ✅ | — | — | — |
| Scored by ACE Bench today | ✅ | ✅ | — | — | — |

**Why L3–L5 are not implemented yet.** L1 and L2 are *read-only* — the agent investigates and
reports, so they can be scored against a deployed environment without ever changing it. L3 adds
recommendation/reasoning scoring; L4 and L5 require the agent to **execute changes**, which
means the harness needs:

1. **Sandboxed execution** — a policy layer that mediates and bounds what the agent may do
   (dry-run, rollback, blast-radius limits).
2. **Post-action state verification** — comparing environment state before/after to confirm the
   agent achieved the goal safely.
3. **Closed-loop infrastructure** — for L5, the observe→analyze→plan→execute→verify loop.

Building that execution + verification infrastructure is the next milestone; until then, L3–L5
remain specified-but-unscored.

---

*Source: "CCB: CloudOps Competency Benchmark for Evaluating Agentic AI for Autonomous CloudOps"
(Vaidhyanathan et al., IIIT Hyderabad / MontyCloud), §4.1 "Five-Level Autonomy Model", Table 1.*
