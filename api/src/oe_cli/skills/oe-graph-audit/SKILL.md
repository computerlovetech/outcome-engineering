---
name: oe-graph-audit
description: Use this skill when asked to audit, review, critique, or check an Outcome Graph for method quality, including outcome/output separation, opportunity/solution separation, known/unknown discipline, assumption-test placement, ICP fit, job coverage, narrative coherence, and whether the graph tells a consistent product story.
---

# OE Graph Audit

Audit an Outcome Graph for product-thinking quality. This complements `oe validate`, which checks structure only.

Use `oe-cli` for graph inspection commands. Use `oe-best-practices` as the source of truth for judging node content.

## Workflow

1. Run structural checks:

```sh
oe validate -g <graph>
oe tree -g <graph>
oe list -g <graph>
```

2. Read the relevant node content with `oe show <ref> -g <graph>`. For a full-graph audit, read the vision, the active strategy, ICPs, jobs, outcomes, opportunities, solutions, assumption tests, and PRDs.

3. Use `oe context <ref> -g <graph>` when auditing a specific node or chain.

4. Read the matching `oe-best-practices` reference for every node type you judge.

5. Report findings by severity, with node refs when possible. Separate structural validity from product-method quality.

## Audit Checks

- Apply the relevant `oe-best-practices` reference for each node.
- Check cross-node coherence: vision -> strategy -> ICP/job -> outcome -> opportunity -> solution -> assumption test / PRD should form a believable product story.
- Check job discipline: every job names a circumstance, forces of progress, and what the customer hires today; every job references an ICP; top-level opportunities connect to a job (directly or inherited); jobs are progress statements, not tasks, aspirations, or features.
- Flag parent/child mismatches: repetition, level jumps, contradictions, generic wording, or children that do not make the parent more actionable.
- Distinguish structural validity from product-method quality.
- Do not invent evidence, customers, metrics, or strategic decisions while recommending fixes.

## Output Format

Keep the audit direct:

- Start with whether `oe validate` passed.
- List findings first, ordered by severity.
- Include concrete fix recommendations.
- Call out strong parts of the graph so the user knows what to preserve.
- End with the highest-leverage next changes.
