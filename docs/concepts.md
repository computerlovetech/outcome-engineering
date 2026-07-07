# The Concepts of Outcome Engineering

**Status: working design document.** This is a first-principles account of every
concept in the Outcome Graph — what each one uniquely explains, where the
boundary to its neighbors runs, why it earns its place as a distinct node kind,
and where the framework is currently weak. It is deliberately critical: the
framework is under development and this document exists to pressure-test it,
not to defend it.

The current kinds (see `oe_core/model.py`): **vision**, **strategy**, **ICP**,
**job**, **outcome**, **opportunity**, **solution**, **assumption test**,
**PRD**, plus the **flywheel** as a separate cyclic structure.

---

## 1. First principles: what the graph is

The Outcome Graph is not a task tracker and not a wiki. It is a **falsifiable
argument** — a chain of reasoning from a durable purpose down to concrete
work, written so that humans and agents can challenge any link in the chain:

> We want to create future **V** (vision). Given today's constraints, our
> current bet for moving toward it is **S** (strategy). We serve people **P**
> (ICPs) who are trying to make progress **J** (jobs). We will know the bet is
> working when we observe changed state **O** (outcomes). The needs blocking
> that change are **N** (opportunities). We intervene with **I** (solutions),
> which rests on beliefs **B** (assumption tests) and, once believed, is
> specified as **R** (PRDs). The wins compound through loop **F** (flywheel).

From this framing we can derive the test a concept must pass to deserve being
a **separate node kind** rather than a paragraph inside another node. It must
differ from its neighbors on at least three of these four axes:

1. **Unique question.** It answers a question no other kind answers.
2. **Distinct lifecycle.** It changes at a different rate, so separating it
   isolates churn (a strategy pivot must not force rewriting the jobs).
3. **Distinct falsifier.** It is validated or killed by a different kind of
   evidence (interviews kill jobs; metrics kill outcomes; experiments kill
   solutions; nothing kills a vision except abandonment).
4. **Distinct epistemic status.** It is *chosen*, *discovered*, *invented*, or
   *proven* — and confusing these is precisely the failure mode the framework
   exists to prevent (e.g. treating an invented solution as a discovered need).

Every boundary dispute below is settled by these axes.

## 2. The concept table

| Concept | Question it answers | Epistemic status | Lifecycle / churn | Falsified by | Cardinality | Lineage |
|---|---|---|---|---|---|---|
| **Vision** | What durable future do we exist to create, for whom? | Chosen (commitment) | Years–decades; survives many strategies | Nothing short of abandonment; judged by whether it still guides decisions | 1 per graph | Product vision canon (Cagan et al.) |
| **Strategy** | What is our current bet — where do we play and how do we win, under today's constraints? | Chosen (bet) | One dated period; superseded, not edited forever | Outcomes not moving during its period | Sequential, non-overlapping periods (enforced) | Rumelt (*Good Strategy Bad Strategy*), Biddle |
| **ICP** | Who, specifically, are we choosing to serve first? | Chosen, then confirmed | Quarters–years; sharpened by evidence | Market response: they don't buy, adopt, or struggle as described | Few per graph | Sales/marketing ICP practice; personas |
| **Job** | What progress is that person trying to make, in what circumstance? | Discovered (fact about the world) | Years; solution-agnostic, survives pivots | Customer interviews, switch behavior | Few per graph; root-level, shared | JTBD (Christensen, Moesta, Ulwick) |
| **Outcome** | What changed state would prove the current bet is working? | Chosen (target), then measured | One strategy cycle | Metrics: the change doesn't happen | Several per graph; root-level | Seiden (*Outcomes Over Output*), Torres |
| **Opportunity** | Which specific unmet need, pain, or desire, if addressed, would drive this outcome? | Discovered (from research) | Weeks–months; scoped to one outcome | Evidence the need isn't real, common, or causal | Many, tree-structured under outcomes | Torres (opportunity solution tree) |
| **Solution** | What intervention might address this need, and by what mechanism? | Invented (hypothesis) | Weeks; cheap to kill | Its own assumption tests | Many per opportunity (by design) | Torres; Lean canon |
| **Assumption test** | What is the cheapest credible way to learn whether one risky belief holds? | Instrument (produces evidence) | Days–weeks; consumed once run | N/A — it *is* the falsifier | Several per solution | Torres; Bland & Osterwalder (*Testing Business Ideas*) |
| **PRD** | What must be true of the delivered product? (why + what, never how) | Committed specification | Lives with delivery of one solution | Acceptance criteria failing | 0–1+ per solution | PRD practice, as reformed by Cagan's critique |
| **Flywheel** | How do individual wins compound into self-reinforcing momentum? | Believed causal loop | Years; the systemic theory of the business | Loop segments that measurably don't feed the next | 1 per graph; cyclic | Collins (*Good to Great*, *Turning the Flywheel*) |

Read down the epistemic column and a gradient appears — this is the deep
structure of the framework:

- **Chosen** (vision, strategy, ICP, outcome-as-target): commitments we make.
- **Discovered** (job, opportunity): facts about customers we find.
- **Invented** (solution): hypotheses we generate.
- **Proven** (assumption test → PRD): beliefs converted into evidence, then
  into commitments to build.
- **Synthesized** (flywheel): the loop that explains why the wins compound.

The graph's value is keeping these apart. Almost every product-thinking
failure is a category error across this gradient: shipping an invention as if
it were a discovery, stating an output as if it were an outcome, writing an
aspiration as if it were a strategy.

## 3. Each concept and its boundaries

### 3.1 Vision

**Uniquely explains:** the durable *destination* — the future state of the
customer's world that outlives every strategy, and the criterion of last
resort when strategies compete ("which option moves us toward the future we
exist to create?").

**Boundary with strategy:** the vision makes no reference to today's
constraints, competitors, or resources; the moment text starts choosing under
constraint ("we will focus on X first because Y"), it has become strategy. The
model encodes this boundary structurally: strategies carry `starts`/`ends`
dates and may not overlap; the vision carries no dates and warns if
duplicated. A vision that changes when the strategy changes was never a
vision.

**Why it must be separate:** without a fixed destination, "strategy" degrades
into a sequence of local optimizations with no direction to argue from. It
fails the falsifier axis in an *informative* way — being the one node no
evidence can kill is exactly its job; everything else in the graph is
disposable relative to it.

### 3.2 Strategy

**Uniquely explains:** the *current bet* — the diagnosis of what actually
stands between here and the vision, and the choice of where to play and how
to win right now. Following Rumelt: a diagnosis of the challenge plus a
guiding policy; ambition without diagnosis is not strategy. The best-practices
reference operationalizes this as: clear choice, named challenge, defined
wedge (ICP + job to win first), logic of advantage.

**Boundary with vision:** dated and disposable vs. durable (above).

**Boundary with outcome:** strategy is the *reasoning*; outcomes are the
*observable checkpoints* of that reasoning. If a strategy node contains
measurable changed states, those lines are outcomes that should be extracted.
If an outcome contains rationale about market conditions and wedges, that's
strategy leaking downward. The one-way test: a strategy can fail even with
well-formed outcomes (wrong bet, right instrumentation); an outcome can fail
even under a correct strategy (right bet, wrong checkpoint). Different
falsifiers → different kinds.

**Why it must be separate:** it is the only node whose *supersession* is part
of its semantics — the model enforces sequential non-overlapping periods, so
the graph accumulates a history of bets. Fusing it into vision destroys the
vision's durability; fusing it into outcomes hides the reasoning that makes
the outcomes coherent with each other.

### 3.3 ICP

**Uniquely explains:** *who* — the deliberately narrow choice of customer,
team, or buyer to serve first, concrete enough that a reader can say who is
in and who is out.

**Boundary with job:** the sharpest boundary in the framework, because the
two are attributes of different things. An ICP is a property of *people* (who
they are, their lived context); a job is a property of a *situation* (the
progress being sought when a circumstance arises). The model encodes the
direction of the relationship: jobs reference the ICPs who have them —
several ICPs can share a job, one ICP can have several jobs. Demographic or
firmographic detail belongs in the ICP; anything about struggle, progress, or
circumstance belongs in a job.

**Boundary with strategy:** choosing an ICP *is* a strategic act (the wedge),
but the ICP node holds the *description* of the segment while the strategy
holds the *argument* for choosing it now. This lets the description survive a
strategy change (the segment is still real; we're just no longer leading with
it).

**Why it must be separate:** JTBD orthodoxy (Christensen) argues the job, not
the customer, is the unit of analysis — so a pure-JTBD design would drop
ICPs. The framework keeps them, and is right to: go-to-market is targeted at
people, not jobs; outcomes and opportunities need "for whom?" answered
concretely to be judgeable; and referencing (rather than embedding) the ICP
lets many nodes share one definition of the audience. This is a deliberate
divergence from JTBD purism, and it should stay — but see the critique (§5.7)
on the name.

### 3.4 Job

**Uniquely explains:** the *demand side* — the progress a customer is trying
to make in a circumstance, why the struggle arises, what they hire today, and
the forces (push, pull, anxiety, habit) that govern switching. It is the only
node kind that describes the world as it is *independent of our product's
existence*. Everything below outcome describes our response; the job would
still be true if the company folded tomorrow.

**Boundary with ICP:** person vs. situation (above).

**Boundary with opportunity:** this is the framework's most contested border,
because both are "customer need"-shaped, and Torres' own definition of
opportunity ("needs, pains, desires") overlaps JTBD language. The framework
resolves it on the lifecycle and scope axes:

- A **job** is durable, solution-agnostic, and *shared* — it lives at the
  root, outside the trace chain, and many outcomes/opportunities reference it.
- An **opportunity** is a *specific* unmet need *within* a job's progress,
  scoped to exactly one parent outcome, with a much shorter life.

Practical tests: if it would survive a strategy pivot and makes sense with no
product at all, it's a job. If it explains where to intervene *to drive this
particular outcome*, it's an opportunity. If it names a feature, it's a
solution in disguise. The known smell "a job that duplicates an opportunity
one level down" is the sign the boundary was missed.

**Why it must be separate:** without root-level jobs, durable customer
knowledge gets trapped inside whichever outcome's subtree first discovered
it, then dies when that outcome is retired. Jobs are the graph's reusable
library of customer understanding; opportunities are per-bet instantiations
of it. (Torres' original tree has no jobs layer — teams often improvise one
by making top-level opportunities job-shaped. Making it explicit and
root-level is one of this framework's genuine contributions; see §5.2.)

### 3.5 Outcome

**Uniquely explains:** *proof* — the changed state (in behavior, usage,
decision quality, learning, or business result) that would demonstrate the
current strategy is working. Per Seiden, the essential discipline is
outcome ≠ output: outputs are what gets shipped; outcomes are what changes
because of it.

**Boundary with strategy:** reasoning vs. checkpoint (§3.2).

**Boundary with solution/output:** the hard-separation rule. If deleting
every feature name from the node leaves nothing, it was an output all along.

**Boundary with opportunity:** an outcome states the change *we* want to see;
an opportunity states a need *the customer* has. Direction of desire is the
test: outcomes are company-voiced ("activation doubles"), opportunities must
be customer-recognizable ("I can't tell if it worked"). A company goal
phrased as a customer need is the smell on one side; a pain list with no
outcome to drive is the smell on the other.

**Why it must be separate:** it is the hinge of the whole graph — the point
where chosen strategy meets discovered reality, and the root of the trace
chain. Everything above it justifies *why this change matters*; everything
below it explains *how we intend to cause it*.

### 3.6 Opportunity

**Uniquely explains:** *where to intervene* — the specific unmet need, pain,
or desire whose resolution would plausibly drive the parent outcome. It is
the framework's unit of discovery: opportunities emerge from interviews and
observation, not brainstorming.

**Boundary with job:** durable shared progress vs. scoped specific need
(§3.4).

**Boundary with solution:** need vs. intervention. Two tests: (a) could the
customer say it? (b) the multiple-solutions test — if only one plausible
solution addresses it, it is that solution restated as a need; ask "why?"
until the underlying need appears.

**Boundary with its own children (nested opportunities):** opportunities
nest to decompose a broad need into addressable ones. The guidance to
structure top-level opportunities around *moments in the customer's
experience* — using the referenced job's steps as the map — is what keeps
nesting from becoming an arbitrary taxonomy.

**Why it must be separate:** it decouples the problem space from the solution
space, which is the entire point of the Torres lineage — teams that skip it
jump from outcome to pet feature and can never explain why any given solution
should move the metric. The opportunity is that explanation.

### 3.7 Solution

**Uniquely explains:** *the intervention and its mechanism* — what we might
build, change, teach, or offer, and *why* that would affect the opportunity.
The mechanism requirement is what elevates a solution above a backlog item:
it must state the causal story that the assumption tests will then attack.

**Boundary with opportunity:** intervention vs. need (§3.6).

**Boundary with assumption test:** a solution *reveals* its risky beliefs but
must not *test* them inline; the evidence work lives in child nodes. This
keeps the solution stable while evidence accumulates around it.

**Boundary with PRD:** a solution is a falsifiable candidate ("might build");
a PRD is a commitment ("will deliver, to these criteria"). See §3.9.

**Why it must be separate:** it is the only *invented* node — the sole place
where creativity enters the graph — and by design there should be several per
opportunity. Making solutions cheap, explicit, and disposable is what allows
the graph to kill ideas without killing the understanding (opportunity, job)
they were attached to.

### 3.8 Assumption test

**Uniquely explains:** *how confidence changes* — the smallest credible
instrument for learning whether one risky belief behind a solution is true,
with the evidence threshold defined before running it.

**Boundary with solution:** belief-holder vs. evidence-maker. One test per
risky assumption — never "test the solution."

**Boundary with PRD:** both are children of solution but face opposite
directions: the assumption test faces *backward into discovery* (is this
solution worth building?), the PRD faces *forward into delivery* (what must
the built thing satisfy?). An assumption test is consumed by the decision it
enables (continue / change / stop); a PRD is consumed by a build.

**Why it must be separate:** it forces the riskiest-assumption discipline
(Bland's mapping of desirability, viability, feasibility; Torres adds
usability and ethics) into the structure itself. Folding tests into the
solution body produces exactly the failure the literature documents: evidence
defined *after* the fact to flatter the idea.

### 3.9 PRD

**Uniquely explains:** *the handoff* — the bridge from validated discovery to
delivery: why the work matters, what must be true from the user's
perspective, acceptance criteria, and preserved unknowns — never the how.

**Boundary with solution:** hypothesis vs. commitment (§3.7).

**Boundary with everything below it:** the PRD is where the Outcome Graph
deliberately *stops*. Architecture, schemas, and tickets belong to delivery
tools; requiring the PRD to trace back through solution → opportunity →
outcome → strategy → vision is what makes it the compressed export of the
entire argument.

**Why it earns its place (with reservations):** Cagan's critique — that PRDs
are typically written *instead of* discovery — is answered structurally here:
a PRD can only exist under a solution, which sits under an opportunity and an
outcome, so the discovery chain is at least visible at the door. But the
model does not yet *enforce* that any evidence preceded it; see §5.4.

### 3.10 Flywheel

**Uniquely explains:** *compounding* — the self-reinforcing causal loop
(Collins: A almost inevitably drives B, B drives C, and C feeds back into A)
that explains why wins accumulate into momentum rather than remaining
isolated. It is deliberately a different *shape* of structure: every other
concept lives in an acyclic tree of justification; the flywheel is a cycle,
because feedback loops cannot be expressed in a hierarchy. Validation even
enforces loop semantics: every flywheel node must name a next step and
explain *why* it causes it.

**Boundary with strategy:** strategy is a dated bet that gets superseded; the
flywheel is the durable systemic theory of the business that strategies take
turns accelerating. Different segments of the same flywheel may be pushed by
successive strategies.

**Boundary with outcomes:** outcomes are point-in-time changed states;
flywheel nodes are recurring stages of a loop. An outcome can *evidence* that
a flywheel segment is turning — which is exactly the link the model currently
fails to record (§5.5).

**Why it must be separate:** the trace chain answers "why does this work
matter?"; only the flywheel answers "why does winning *this* make the next
win cheaper?" No tree node can express that, because trees can't contain
cycles.

## 4. How the concepts compose

```
            CHOSEN                     DISCOVERED
   vision ──guides──▶ strategy        icp ◀──who has──┐
                          │ wedge names ▲             │
                          ▼            (refs)        job   (root-level,
   PROOF   outcome ───references──────────────────────┘    durable library)
              │  ▲(should reference strategy — gap, §5.1)
   trace      ▼
   chain   opportunity (nests; refs jobs + icps)
              │
              ▼
   INVENTED solution ─── reveals beliefs
              │                    │
              ▼                    ▼
   EVIDENCE assumption-test      prd  ──▶ delivery (outside the graph)

   flywheel: f1 ─▶ f2 ─▶ f3 ─▶ f1   (cyclic; currently unlinked — §5.5)
```

Three relationship mechanisms, each carrying different semantics:

1. **The trace chain (parent/child):** outcome → opportunity → solution →
   assumption-test/PRD. This is the *justification* relation: each child
   exists to serve its parent, and deleting a parent orphans the reasoning
   below it. It is strict (placement rules) because justification must be
   unambiguous.
2. **References (many-to-many):** outcomes/opportunities → jobs;
   outcomes/opportunities/jobs → ICPs. This is the *grounding* relation: it
   attaches shared, durable customer knowledge to bet-specific reasoning
   without duplicating it. References are the right mechanism precisely
   because jobs and ICPs outlive any single trace chain.
3. **Ambient context (vision, current strategy, flywheel):** these attach to
   *everything* implicitly — context assembly injects them into every node's
   context. This is the *orientation* relation: they are premises of every
   argument rather than steps in any particular one.

This three-mechanism design is sound. The critique below is mostly about
places where a relationship that *should* exist is left to convention.

## 5. Critique

Being honest about weaknesses, per the framework's own "challenge everything"
ethos.

### 5.1 Outcomes don't reference the strategy they serve — the biggest gap

Outcome rule 6 says "fit the current strategy," but this is pure convention:
there is no edge from an outcome to a strategy. Consequences:

- When a strategy period ends, its outcomes remain at the root, silently
  reattached (by the "current strategy" convention) to a bet they were never
  designed for. The graph cannot answer "which outcomes belonged to the 2025
  wedge bet?" even though it *dates* the strategies.
- Validation cannot warn about an outcome that fits no strategy, or a
  strategy with no outcomes instrumenting it — both common and serious
  failure modes (Rumelt's "goals mistaken for strategy" in reverse).

**Recommendation:** add `strategy_ref_ids` to outcomes (same mechanism as job
refs) plus advisory validation both ways. This also creates the historical
record — superseded strategies keep their outcomes, and the graph becomes an
archive of bets and their results, which is the raw material for actually
learning.

### 5.2 The job/opportunity boundary is right, but it's policed only by prose

Splitting jobs from opportunities fixes a real ambiguity in Torres' tree
(where durable job-shaped needs and specific pains compete for the same
top-of-tree slots). But the boundary is semantic — durability,
solution-agnosticism, customer-voice — and the data model cannot see any of
it. The framework currently relies entirely on skills and advisory warnings.
That's acceptable *if* acknowledged: expect constant misfiling, and treat
`oe-graph-audit`-style review as a first-class part of the method, not an
add-on. The alternative — encoding the boundary in required fields
(circumstance, forces, alternatives-hired as structured fields on job) — is
worth considering once real usage shows which prose sections actually get
written.

### 5.3 "Outcome" is defined too broadly

The definition admits changed states in "behavior, usage, decision quality,
learning, or business result." Seiden's discipline is narrower — customer
*behavior* change that drives business results — and the breadth here has a
cost: "the team learned X" and "revenue grew" both qualify, so the
output/outcome firewall develops holes ("we shipped the wizard *and learned a
lot*"). Learning goals are legitimate but they are what assumption tests
produce, not what outcomes prove. **Recommendation:** either tighten the
definition to observable behavior/business change, or introduce an explicit
`type` on outcomes (behavior / business / learning) so a graph audit can flag
learning-heavy outcome sets as a discovery smell.

### 5.4 A PRD can exist with zero evidence behind it

The placement rules allow solution → PRD with no assumption tests ever
created. That is structurally the exact anti-pattern Cagan describes: the PRD
written instead of discovery. The framework's answer today is cultural, not
structural. **Recommendation:** an advisory validation — "solution has a PRD
but no assumption tests; what evidence justified committing?" — with a
documented escape hatch (some work *is* legitimately assumption-light:
compliance, parity, infrastructure).

### 5.5 The flywheel floats disconnected

Flywheel nodes reference only each other. The loop that supposedly explains
why the whole enterprise compounds has no recorded relationship to any
outcome, ICP, or job. It risks being what Collins warns against — a wall
poster. **Recommendation:** let flywheel nodes reference the outcomes that
evidence them (and possibly the jobs they serve). Then "is the flywheel
actually turning?" becomes an answerable question: each segment either has
instrumentation or visibly lacks it.

### 5.6 Strategy is a blob where the model could be an argument

For a framework whose thesis is "decompose reasoning into challengeable
nodes," strategy is conspicuously monolithic: diagnosis, wedge, and logic of
advantage all live in one markdown body, guarded only by prose rules. An
agent can challenge a specific opportunity; it cannot challenge "the
diagnosis" as a node, because there isn't one. This may be the right
trade-off (strategy decomposition is where frameworks go to die of
ceremony), but it is a trade-off, and it's currently undocumented. The
minimal structural upgrade with real payoff is §5.1's strategy↔outcome edge;
full Rumelt-style decomposition (diagnosis / guiding policy / coherent
actions as child nodes) should wait for evidence that the blob is failing.

### 5.7 "ICP" is a borrowed name that doesn't quite fit

In sales practice, an ICP is typically a *firmographic* account profile
(B2B: company size, industry, buying triggers). What this framework calls an
ICP — "the specific kind of customer, user, buyer, team, or practitioner…
their lived context" — is closer to a target persona or segment. The concept
is right (see §3.3: keeping "who" out of jobs is correct and a justified
divergence from JTBD purism); the *name* imports expectations it doesn't
meet, and B2B users will look for buyer-vs-user distinctions the model
doesn't make. Either rename (e.g. "audience," "segment") or explicitly
document that OE's ICP covers both account- and person-level targeting, and
that buyer vs. user should be separate ICP nodes when the distinction
matters.

### 5.8 Evidence has no home

Opportunities must be "evidenced," assumption tests must "define evidence
before running" — but evidence itself is never a thing in the graph. Interview
snapshots, test results, and metrics live (at best) pasted into node bodies.
Consequences: an assumption test's plan and its *result* share one markdown
blob with no state (proposed / running / validated / invalidated), and no
node can cite the same interview twice without copy-paste. This is probably
the most valuable *future* concept: a lightweight evidence/insight node (or
even just a status + result convention on assumption tests) would let
validation ask the killer question — "what evidence, exactly?" — of any
opportunity or PRD. Until then, the framework's claim to falsifiability is
aspirational at the leaves.

### 5.9 What should *not* be added

To keep the mini-framework mini, name the anti-scope. Metrics/OKRs as nodes
(measures belong inside outcomes; a metrics tree is a different product),
tasks/tickets (delivery lives elsewhere; the PRD is the boundary), personas
*alongside* ICPs (one "who" concept is enough), and business-model canvases
(the flywheel already carries the systemic story) — all fail the §1 test
against an existing kind, mostly axis 1 (no unique question). Every concept
added multiplies the boundary-policing burden documented above; nine kinds
plus a flywheel is already at the edge of what teams will classify correctly
without agent help.

## 6. Summary judgment

The core is sound and the boundaries, on paper, are the *right* boundaries:
each of the nine kinds plus the flywheel passes the four-axis test of §1, and
the three relationship mechanisms (trace, reference, ambient) carry genuinely
different semantics. The framework's two original contributions — root-level
jobs referenced by the trace chain, and machine-enforced strategy periods —
both survive scrutiny and improve on their sources.

The honest weaknesses are of one family: **the framework's promises outrun
its edges.** Outcomes promise to serve strategies (no edge, §5.1), PRDs
promise validated discovery behind them (no check, §5.4), the flywheel
promises compounding (no instrumentation, §5.5), opportunities promise
evidence (no home for it, §5.8). None of these requires new concepts — they
require new *relationships and advisory validations* among the concepts that
already exist. That is the encouraging conclusion: the ontology is right; the
connective tissue is one iteration behind it.

---

### Sources

- Teresa Torres, [Opportunity Solution Trees](https://www.producttalk.org/opportunity-solution-trees/) and *Continuous Discovery Habits* — outcome/opportunity/solution/assumption-test chain.
- Teresa Torres, [Outcomes vs. Outputs](https://www.producttalk.org/outcomes-vs-outputs/); Josh Seiden, *Outcomes Over Output* — outcome definition.
- Clayton Christensen / Bob Moesta / Tony Ulwick — Jobs-to-be-Done: progress, circumstance, forces, hiring.
- Richard Rumelt, *Good Strategy Bad Strategy* — diagnosis + guiding policy + coherent action; Gibson Biddle, [DHM](https://www.gibsonbiddle.com/strategy).
- David Bland & Alexander Osterwalder, *Testing Business Ideas*; [Strategyzer on assumptions mapping](https://www.strategyzer.com/library/how-assumptions-mapping-can-focus-your-teams-on-running-experiments-that-matter) — riskiest-assumption discipline.
- Jim Collins, [The Flywheel Effect](https://www.jimcollins.com/concepts/the-flywheel.html) — causal loop, momentum, doom loop.
- Marty Cagan, [Discovery vs. Documentation](https://www.svpg.com/discovery-vs-documentation/) — PRD critique.
