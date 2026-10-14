---
name: devils-advocate
description: Stress-test a proposed design, architecture, tech choice, plan, requirements set, or decision — produced by another skill, another LLM, or the user — by posing pointed questions tied to its specific decisions across every relevant angle (failure modes, security, scale, data, cost, reversibility, alternatives, hidden assumptions, and more), resolving each with evidence or a design change, and repeating until no critical gap remains. Ends with a hardened proposal, a risk register, and tripwires. Use when the user asks to challenge, poke holes in, sanity-check, red-team, or play devil's advocate on something. Also use proactively, without being asked, before presenting a non-trivial or hard-to-reverse design or decision as final (for example after tech-stack-advisor, tech-design, or an architecture recommendation of your own).
argument-hint: [path-to-proposal | "decision text" | (empty = the latest proposal in this conversation)] [--rounds N]
---

# Devil's Advocate

Find out where the proposal breaks before reality does, then fix it. You are its toughest
honest critic, not its opponent: every challenge has to be specific, plausible, and settled
with evidence, a change to the design, or a risk someone has explicitly accepted.

```
DA="python3 <this-skill-dir>/scripts/devils_advocate.py"
```

Keep `ledger.json` in a scratch directory. It is the single record of the run; the script
checks it and writes the report from it.

## When the model should run this unprompted

Run it before presenting as final any design, architecture, stack choice, migration, data model,
security model, rollout plan, or decision that is costly to reverse, affects more than one
component or team, or that the user is about to build on. Skip it for trivial or easily
reversed choices, and don't run it twice on an unchanged proposal. When running unprompted, say
so in one line ("Stress-testing this before I hand it over") and keep the user-facing output to
the summary in step 7.

## 1. Pin down the proposal

Use the argument: a file path, quoted text, or, if empty, the latest proposal in this
conversation. Set `kind` to `design`, `decision`, `plan`, `requirements`, `code`, or `other`.
Then `$DA init --subject "<name>" --kind <kind> --source <path> > ledger.json`.

Read the proposal and its context: the requirements it serves (`docs/blueprint/PRD.md`,
`02-clarified-requirements.md`), the repo's rules, and existing code via `repo-index` when the
proposal touches a codebase. Questions the code or docs already answer are not worth asking.

Extract every load-bearing statement into `decisions`, typed `decision`, `assumption`
(including unstated ones you had to infer), `constraint`, or `goal`, with IDs `D1, D2, …`.

## 2. Steelman first

Write the strongest case for the proposal in `steelman`: what it optimizes for and why a smart
person would choose it. If you can't steelman it, you don't understand it well enough to attack
it yet. This also stops you from inventing objections the author already handled.

## 3. Attack, lens by lens

`$DA lenses --kind <kind>` lists the applicable lenses (source:
[references/lenses.md](references/lenses.md)). For each lens, turn its question templates into
**relative** questions: aimed at a named decision, using the proposal's own components, numbers,
and words. Record each as a challenge:

```json
{"id": "C4", "round": 1, "lens": "failure", "target": "D3", "severity": "high",
 "question": "D3 keeps sessions on one Redis node; when it restarts during a deploy, what happens to in-progress checkouts?",
 "scenario": "Deploy restarts the node at peak; ~2k carts vanish and users must start over.",
 "status": "open"}
```

- **Severity** — `critical`: the goal fails, data is lost or exposed, or the cost is irreversible;
  `high`: a likely, serious failure or major rework; `medium`: a real but contained cost;
  `low`: a polish or minor risk. Rate by likelihood × impact, not by how clever the question is.
- **No scenario, no challenge.** If you can't describe a concrete way it goes wrong, drop it.
- Prefer a few sharp challenges to many vague ones. A lens with nothing material gets
  `coverage.<lens> = {"status": "clear", "note": "<what you checked>"}`; a lens that truly can't
  apply gets `"n/a"` with the reason. Never leave a lens unexamined.
- Look at where decisions interact as well as at each one alone: two reasonable choices that
  fail together (cache TTL vs. permission revocation, retries vs. non-idempotent writes).

**Independence:** if you wrote the proposal yourself in this conversation, your reasoning will
defend it. When the host can run a subagent, give it only the proposal text, the `decisions`
list, and the lens file, ask it for challenges in the format above, then merge its list with yours.

## 4. Resolve every challenge

Work highest severity first. Each challenge ends in exactly one status:

| Status | Required field | Meaning |
|---|---|---|
| `refuted` | `evidence` | The proposal already handles it; cite `file:line`, a doc section, a measurement, or a source. |
| `mitigated` | `resolution`, `change` | The proposal is changed to handle it; add the change to `changes` (`CH1`, …, with `affects`). |
| `accepted` | `resolution`; `signoff` if critical/high | The risk is knowingly kept, with the reason and a tripwire. |
| `open` | — | It can't be settled without the user. |

Never refute from optimism. "Unlikely" is not evidence, and an answer you made up is worse than
an open question. Settle `open` challenges with the user through **AskUserQuestion** (at most
4 per round, highest severity first). Give each one the scenario, 2–3 concrete options (a
mitigation, accept with a tripwire, or rethink the decision), and your recommendation.
`signoff` records who accepted the risk (e.g. `"user"`). Never sign off a critical or high
risk on the user's behalf.

## 5. Attack the revised proposal

Mitigations are new design, and new design has holes. Start the next round (`"round": 2, …`)
aimed at what changed and at anything the changes touch. Repeat until a round raises no new
critical or high challenge. Default cap: 3 rounds (`--rounds N` overrides). If the cap is hit
while still raising blocking challenges, ask the user whether to continue or stop. Stopping
records `convergence_waived_by`, and the report says the proposal did not converge.

Add `tripwires` (`{"signal", "action"}`): observable signs that a mitigation or accepted risk is
failing in production, and what to do then, such as a metric threshold, an error pattern, or a
cost line.

## 6. Gate

`$DA gate ledger.json` exits non-zero while any blocker remains. The rules are computed, not
chosen:

- **Not hardened**: a lens left unexamined, an open critical/high challenge, a refutation with
  no evidence, a mitigation with no recorded change, an accepted critical/high risk with no
  sign-off, a challenge not tied to an extracted decision, or a last round that still raised a
  critical/high challenge.
- **Hardened with residual risks**: no blockers, but there are accepted risks, open
  medium/low challenges, or warnings.
- **Hardened**: none of the above.

Fix the blockers and run it again. Don't edit the ledger to make the gate pass.

## 7. Deliver the hardened proposal

1. **Apply the changes to the proposal.** If another skill produced it in this session (e.g.
   `TECHNICAL-DESIGN.md`, `03-tech-stack.md`), edit that artifact so each `CH` lands where it
   belongs. If the user wrote it, show the revised version and ask before editing their file.
   A proposal from chat is restated in full, revised.
2. **Write the report.** `$DA render ledger.json --date <today> --out <path>` with
   `docs/blueprint/DEVILS-ADVOCATE.md` inside the product-blueprint pipeline, else
   `docs/devils-advocate/<slug>.md`. For a small chat-only decision, skip the file and put the
   verdict, changes, and residual risks in the reply.
3. **Tell the user**: the verdict, the 3 most serious challenges and how each was settled, what
   changed in the proposal, residual risks with their tripwires, and anything that still needs
   their decision. Don't call it "fool-proof". Name what was checked and what risk remains.

Return control to the calling skill if there is one. That skill should continue from the
hardened version, not the original.
