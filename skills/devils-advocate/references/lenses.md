# Devil's advocate lenses

Each lens is one angle of attack. `devils_advocate.py` parses this file: a lens is a `###`
heading of the form `` ### `id` — Name ``, then an `Applies to:` line, then bullet questions.
Keep that shape when editing.

The questions are **templates**. Never ask them as written: bind each one to a specific
decision or assumption from the proposal (`D3`, `A2`, …), so the question can only be answered
by someone who read *this* proposal. "What if the database fails?" is generic. "D3 puts
sessions in a single Redis node; when that node restarts mid-checkout, which carts are lost
and who notices?" is relative.

Kinds: `design`, `decision`, `plan`, `requirements`, `code`, `other` (`other` gets every lens).

### `framing` — Problem framing & goals
Applies to: design, decision, plan, requirements, code
- What problem does this actually solve, and for whom? Would the people who have it agree?
- Which goal does `<decision>` serve, and how would we know a month later that it worked?
- Is this a symptom of a deeper problem that `<decision>` leaves in place?
- If the stated goal were achieved some other way tomorrow, would anyone still want this?

### `requirements` — Requirements fit & traceability
Applies to: design, plan, requirements, code
- Which requirement has no home in the proposal, and which part of the proposal has no requirement?
- Does `<decision>` meet the requirement's acceptance criteria, or only its title?
- Where do two requirements pull against each other, and which one did `<decision>` quietly drop?
- What did the user ask for that the proposal reinterpreted?

### `assumptions` — Hidden assumptions
Applies to: design, decision, plan, requirements, code
- What must be true for `<decision>` to work, and what evidence says it is true today?
- Which assumption, if wrong, causes the most rework? How cheaply can we test it before committing?
- What number (load, size, budget, headcount, latency) is assumed rather than measured?
- What does `<decision>` assume about how users, operators, or upstream systems behave?

### `alternatives` — Alternatives & opportunity cost
Applies to: design, decision, plan, requirements
- What is the strongest alternative to `<decision>`, argued by its best advocate?
- What happens if we do nothing, or the smallest possible thing?
- Is there a boring, proven option `<decision>` passed over for a novel one? Why?
- What does choosing `<decision>` stop us from doing later?

### `failure` — Failure modes & resilience
Applies to: design, decision, plan, code
- When the component behind `<decision>` fails, slows down, or returns garbage, what does the user see?
- What is the blast radius: one request, one tenant, or everyone?
- What happens on partial failure, timeout, retry, or a duplicate message?
- How does it recover, and what state is left behind that a human must clean up?

### `edge-cases` — Edge cases & invalid input
Applies to: design, requirements, code
- What does `<decision>` do with empty, huge, malformed, duplicated, or out-of-order input?
- What about concurrency: two users, two tabs, two workers touching the same thing at once?
- Time zones, DST, leap days, locales, unicode, currency rounding: which of these can reach it?
- What is the first input a hostile or careless user would try?

### `scale` — Scale & performance
Applies to: design, decision, code
- At 10× and 100× today's load or data size, what breaks first under `<decision>`?
- Which path is O(n) per request, or does a fan-out that grows with users?
- What is the latency budget, and where does `<decision>` spend it?
- What happens during a traffic spike, a backfill, or a cold start?

### `security` — Security, privacy & abuse
Applies to: design, decision, plan, requirements, code
- Who can reach `<decision>`'s surface, and what can an unauthenticated or low-privilege caller do?
- Where is trust assumed across a boundary that an attacker controls?
- What sensitive data does it store, log, or send, and who can read it?
- How would someone abuse it for spam, fraud, scraping, or resource exhaustion?
- What happens when a secret, token, or key leaks?

### `data` — Data integrity, consistency & migration
Applies to: design, decision, code
- What is the source of truth for each piece of data `<decision>` touches?
- Where can two copies disagree, and which one wins?
- How are existing data and in-flight requests migrated, and can the migration be rolled back?
- What is lost, duplicated, or corrupted if a write half-completes?
- How long is data kept, and how is it deleted when someone asks?

### `operability` — Operability & observability
Applies to: design, decision, plan, code
- At 3 a.m., how does on-call learn `<decision>` is broken before users report it?
- What logs, metrics, and alerts exist, and which question can't they answer?
- How is it deployed, configured, and rolled back, and how long does a rollback take?
- What routine toil does it create (rotations, cleanups, manual approvals)?

### `cost` — Cost & resources
Applies to: design, decision, plan
- What does `<decision>` cost to build, run, and maintain, and how does the run cost grow with usage?
- Which cost is easy to overlook: egress, licences, support, on-call, training?
- What is the cheapest version that still meets the goal?

### `reversibility` — Reversibility & lock-in
Applies to: design, decision, plan
- Is `<decision>` a one-way or two-way door? What would it cost to undo in six months?
- What becomes locked in (vendor, data format, public API, contract)?
- Can we ship it behind a flag, to a subset of users, or in shadow mode first?

### `dependencies` — Dependencies & third parties
Applies to: design, decision, plan, code
- What does `<decision>` depend on that we don't control, and what happens when it changes, rate-limits, or disappears?
- Are the dependencies maintained, licensed compatibly, and free of known vulnerabilities?
- Which other team or system must change, and have they agreed?

### `people` — People, process & ownership
Applies to: design, decision, plan, requirements
- Who owns `<decision>` after launch, and do they have the skills to run it?
- Who is affected but wasn't consulted?
- What happens when the one person who understands it leaves?

### `delivery` — Sequencing, timeline & incremental delivery
Applies to: plan, design, decision
- What is the smallest slice that delivers value and tests the riskiest assumption first?
- Which step blocks everything after it, and what if it slips?
- What is the plan if the estimate is wrong by 2×?
- What are the explicit go/no-go checkpoints?

### `testability` — Testability & verification
Applies to: design, plan, requirements, code
- How would we prove `<decision>` works before users rely on it?
- Which behaviour is hard to test (time, randomness, third parties, concurrency), and how is that handled?
- What test would fail if `<decision>` were silently broken?
- Which requirement can't be verified as written?

### `compliance` — Legal, compliance & ethics
Applies to: design, decision, requirements, plan
- Which regulations (privacy, accessibility, financial, sector-specific) apply to `<decision>`?
- What would a regulator, auditor, or journalist ask about it?
- Who could be harmed or excluded by it, and is that acceptable?

### `second-order` — Second-order effects & incentives
Applies to: design, decision, plan, requirements
- What behaviour does `<decision>` reward, and how will people game it?
- What adjacent system, team, or metric gets worse because this gets better?
- What will this make harder to change a year from now?

### `ux` — User experience & adoption
Applies to: design, requirements, plan
- What does the user have to learn, change, or give up because of `<decision>`?
- What does a first-time user, a power user, and a user with a disability each experience?
- What does the user see when things go wrong, and can they recover alone?
- Why would someone choose this over what they do today?
