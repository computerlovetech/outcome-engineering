"""Unit tests for the pure domain core (placement, slugs, strategy dates,
ICP references, selectors, cascade deletes, validation, context)."""

from __future__ import annotations

import uuid
from datetime import date

import pytest

from oe_core import rules, selector, validation
from oe_core.context import context_markdown
from oe_core.errors import (
    AmbiguousSelectorError,
    CascadeRequiredError,
    IcpReferenceError,
    NotFoundError,
    PlacementError,
    SlugError,
    StrategyDateError,
)
from oe_core.model import Flywheel, FlywheelNode, GraphSnapshot, Node, allowed_child_kinds, valid_slug


def make_node(kind: str, slug: str, parent_id: str | None = None, **kwargs) -> Node:
    return Node(
        id=str(uuid.uuid4()),
        kind=kind,
        slug=slug,
        title=kwargs.pop("title", slug),
        content=kwargs.pop("content", f"# {slug}\n\nBody."),
        parent_id=parent_id,
        **kwargs,
    )


@pytest.fixture
def snapshot() -> GraphSnapshot:
    vision = make_node("vision", "vision")
    strategy = make_node("strategy", "s1", starts=date(2026, 1, 1), ends=date(2026, 6, 30))
    icp = make_node("icp", "founders")
    outcome = make_node("outcome", "activation", icp_ref_ids=(icp.id,))
    opp = make_node("opportunity", "onboarding", parent_id=outcome.id)
    sol = make_node("solution", "wizard", parent_id=opp.id)
    at = make_node("assumption-test", "signup-drop", parent_id=sol.id)
    return GraphSnapshot(nodes=[vision, strategy, icp, outcome, opp, sol, at])


def get(snapshot: GraphSnapshot, ref: str) -> Node:
    return selector.resolve(snapshot, ref)


# --- placement -------------------------------------------------------------

def test_allowed_child_kinds():
    assert allowed_child_kinds("root") == {"vision", "strategy", "icp", "outcome"}
    assert allowed_child_kinds("outcome") == {"opportunity"}
    assert allowed_child_kinds("opportunity") == {"opportunity", "solution"}
    assert allowed_child_kinds("solution") == {"assumption-test", "prd"}
    assert allowed_child_kinds("prd") == set()


def test_create_valid_placements(snapshot):
    rules.check_create(snapshot, kind="outcome", slug="retention", parent=None)
    outcome = get(snapshot, "outcome.activation")
    rules.check_create(snapshot, kind="opportunity", slug="new-opp", parent=outcome)
    opp = get(snapshot, "opportunity.onboarding")
    rules.check_create(snapshot, kind="opportunity", slug="nested", parent=opp)
    rules.check_create(snapshot, kind="solution", slug="another", parent=opp)
    sol = get(snapshot, "solution.wizard")
    rules.check_create(snapshot, kind="prd", slug="wizard-prd", parent=sol)


def test_create_rejects_bad_placements(snapshot):
    outcome = get(snapshot, "outcome.activation")
    sol = get(snapshot, "solution.wizard")
    with pytest.raises(PlacementError):
        rules.check_create(snapshot, kind="solution", slug="x", parent=outcome)
    with pytest.raises(PlacementError):
        rules.check_create(snapshot, kind="opportunity", slug="x", parent=None)
    with pytest.raises(PlacementError):
        rules.check_create(snapshot, kind="outcome", slug="x", parent=sol)
    with pytest.raises(PlacementError):
        rules.check_create(snapshot, kind="banana", slug="x", parent=None)


def test_only_one_vision(snapshot):
    with pytest.raises(PlacementError, match="already has a vision"):
        rules.check_create(snapshot, kind="vision", slug="v2", parent=None)


# --- slugs -----------------------------------------------------------------

def test_slug_format():
    assert valid_slug("messy-product-assumptions")
    assert valid_slug("a1")
    assert not valid_slug("Bad")
    assert not valid_slug("has space")
    assert not valid_slug("-lead")
    assert not valid_slug("double--dash")
    assert not valid_slug("")


def test_duplicate_slug_same_kind_rejected(snapshot):
    with pytest.raises(SlugError, match="already exists"):
        rules.check_create(snapshot, kind="outcome", slug="activation", parent=None)


def test_same_slug_different_kind_allowed(snapshot):
    rules.check_create(snapshot, kind="icp", slug="activation", parent=None)


# --- strategy dates ----------------------------------------------------------

def test_strategy_requires_dates(snapshot):
    with pytest.raises(StrategyDateError, match="must declare starts and ends"):
        rules.check_create(snapshot, kind="strategy", slug="s2", parent=None)


def test_strategy_rejects_inverted_range(snapshot):
    with pytest.raises(StrategyDateError, match="on or before"):
        rules.check_create(
            snapshot, kind="strategy", slug="s2", parent=None,
            starts=date(2027, 1, 1), ends=date(2026, 1, 1),
        )


def test_strategy_rejects_overlap(snapshot):
    with pytest.raises(StrategyDateError, match="overlaps"):
        rules.check_create(
            snapshot, kind="strategy", slug="s2", parent=None,
            starts=date(2026, 6, 30), ends=date(2026, 12, 31),
        )


def test_strategy_allows_adjacent_period(snapshot):
    rules.check_create(
        snapshot, kind="strategy", slug="s2", parent=None,
        starts=date(2026, 7, 1), ends=date(2026, 12, 31),
    )


def test_strategy_update_excludes_self(snapshot):
    node = get(snapshot, "strategy.s1")
    rules.check_strategy_dates(
        snapshot, starts=date(2026, 1, 1), ends=date(2026, 7, 31), exclude_node_id=node.id
    )


def test_non_strategy_cannot_have_dates(snapshot):
    with pytest.raises(StrategyDateError, match="only strategy"):
        rules.check_create(
            snapshot, kind="outcome", slug="dated", parent=None, starts=date(2026, 1, 1), ends=date(2026, 2, 1)
        )


def test_current_strategy(snapshot):
    assert snapshot.current_strategy(date(2026, 3, 1)).slug == "s1"
    assert snapshot.current_strategy(date(2027, 3, 1)) is None


# --- ICP references ----------------------------------------------------------

def test_icp_refs_only_on_outcome_and_opportunity(snapshot):
    icp = get(snapshot, "icp.founders")
    sol = get(snapshot, "solution.wizard")
    with pytest.raises(IcpReferenceError, match="cannot reference ICPs"):
        rules.check_create(snapshot, kind="prd", slug="p", parent=sol, icp_ref_ids=(icp.id,))


def test_icp_ref_must_target_icp(snapshot):
    sol = get(snapshot, "solution.wizard")
    with pytest.raises(IcpReferenceError, match="not an icp"):
        rules.check_icp_refs(snapshot, kind="outcome", icp_ref_ids=(sol.id,))
    with pytest.raises(IcpReferenceError, match="does not resolve"):
        rules.check_icp_refs(snapshot, kind="outcome", icp_ref_ids=(str(uuid.uuid4()),))


def test_related_icps_inherited(snapshot):
    sol = get(snapshot, "solution.wizard")
    icps = snapshot.related_icps(sol)
    assert [icp.ref for icp in icps] == ["icp.founders"]


def test_related_icps_deduped():
    icp = make_node("icp", "devs")
    outcome = make_node("outcome", "o", icp_ref_ids=(icp.id,))
    opp = make_node("opportunity", "p", parent_id=outcome.id, icp_ref_ids=(icp.id,))
    snap = GraphSnapshot(nodes=[icp, outcome, opp])
    assert len(snap.related_icps(opp)) == 1


# --- selectors ---------------------------------------------------------------

def test_resolve_by_ref_slug_and_uuid(snapshot):
    node = get(snapshot, "outcome.activation")
    assert selector.resolve(snapshot, "activation").id == node.id
    assert selector.resolve(snapshot, node.id).id == node.id


def test_resolve_errors(snapshot):
    with pytest.raises(NotFoundError):
        selector.resolve(snapshot, "outcome.nope")
    with pytest.raises(NotFoundError):
        selector.resolve(snapshot, "nope")
    with pytest.raises(NotFoundError):
        selector.resolve(snapshot, str(uuid.uuid4()))
    with pytest.raises(NotFoundError):
        selector.resolve(snapshot, "banana.x")


def test_resolve_ambiguous_bare_slug():
    a = make_node("outcome", "same")
    b = make_node("icp", "same")
    snap = GraphSnapshot(nodes=[a, b])
    with pytest.raises(AmbiguousSelectorError):
        selector.resolve(snap, "same")
    assert selector.resolve(snap, "outcome.same").id == a.id


# --- deletes -----------------------------------------------------------------

def test_delete_requires_cascade_for_descendants(snapshot):
    outcome = get(snapshot, "outcome.activation")
    with pytest.raises(CascadeRequiredError, match="cascade"):
        rules.check_delete(snapshot, outcome, cascade=False)
    descendants = rules.check_delete(snapshot, outcome, cascade=True)
    assert {d.ref for d in descendants} == {
        "opportunity.onboarding", "solution.wizard", "assumption-test.signup-drop"
    }


def test_delete_leaf_without_cascade(snapshot):
    leaf = get(snapshot, "assumption-test.signup-drop")
    assert rules.check_delete(snapshot, leaf, cascade=False) == []


def test_delete_referenced_icp_refused(snapshot):
    icp = get(snapshot, "icp.founders")
    with pytest.raises(CascadeRequiredError, match="referenced by"):
        rules.check_delete(snapshot, icp, cascade=False)


# --- ancestors / tree --------------------------------------------------------

def test_ancestors_chain(snapshot):
    at = get(snapshot, "assumption-test.signup-drop")
    assert [n.ref for n in snapshot.ancestors(at)] == [
        "outcome.activation", "opportunity.onboarding", "solution.wizard"
    ]


def test_children_ordered_by_position():
    parent = make_node("outcome", "o")
    b = make_node("opportunity", "b", parent_id=parent.id, position=1)
    a = make_node("opportunity", "a", parent_id=parent.id, position=0)
    snap = GraphSnapshot(nodes=[parent, b, a])
    assert [n.slug for n in snap.children(parent)] == ["a", "b"]


# --- validation ----------------------------------------------------------------

def test_valid_graph_has_no_issues(snapshot):
    assert validation.validate_graph(snapshot) == []


def test_validate_reports_overlapping_strategies():
    s1 = make_node("strategy", "s1", starts=date(2026, 1, 1), ends=date(2026, 6, 30))
    s2 = make_node("strategy", "s2", starts=date(2026, 6, 1), ends=date(2026, 12, 31))
    issues = validation.validate_graph(GraphSnapshot(nodes=[s1, s2]))
    assert any("overlaps" in issue.message for issue in issues)


def test_validate_reports_missing_strategy_dates():
    s1 = make_node("strategy", "s1")
    issues = validation.validate_graph(GraphSnapshot(nodes=[s1]))
    assert any("must declare starts and ends" in issue.message for issue in issues)


def test_validate_reports_multiple_visions():
    snap = GraphSnapshot(nodes=[make_node("vision", "a"), make_node("vision", "b")])
    assert any("multiple visions" in i.message for i in validation.validate_graph(snap))


def test_validate_reports_bad_placement():
    outcome = make_node("outcome", "o")
    stray = make_node("solution", "s", parent_id=outcome.id)
    issues = validation.validate_graph(GraphSnapshot(nodes=[outcome, stray]))
    assert any("not allowed under outcome.o" in i.message for i in issues)


def test_validate_reports_dangling_icp_ref():
    outcome = make_node("outcome", "o", icp_ref_ids=(str(uuid.uuid4()),))
    issues = validation.validate_graph(GraphSnapshot(nodes=[outcome]))
    assert any("does not resolve" in i.message for i in issues)


def test_validate_flywheel_rules():
    n1 = FlywheelNode(id=str(uuid.uuid4()), slug="a", title="A", content="Because it drives B.", status=None, position=0, next_ids=(str(uuid.uuid4()),))
    n2 = FlywheelNode(id=str(uuid.uuid4()), slug="b", title="B", content="# heading only", status=None, position=1, next_ids=())
    fw = Flywheel(id=str(uuid.uuid4()), slug="growth", title="Growth", content="", status=None, nodes=(n1, n2))
    issues = validation.validate_graph(GraphSnapshot(nodes=[], flywheel=fw))
    messages = " | ".join(i.message for i in issues)
    assert "does not resolve to a flywheel node" in messages
    assert "at least one next step" in messages
    assert "must explain why" in messages


# --- context -------------------------------------------------------------------

def test_context_markdown_structure(snapshot):
    sol = get(snapshot, "solution.wizard")
    md = context_markdown(snapshot, sol)
    assert md.startswith("# Context: solution.wizard")
    assert "## Trace" in md
    assert "- outcome.activation" in md
    assert "- solution.wizard" in md
    assert "## ICPs" in md and "- icp.founders" in md
    assert "## Children" in md and "- assumption-test.signup-drop" in md
    assert "## Vision" in md
    assert "## Ancestor Content" in md
    assert "## Node Content" in md
    assert md.index("## Trace") < md.index("## Node Content")


def test_context_markdown_includes_flywheel():
    n1 = FlywheelNode(id="fw-1", slug="ship", title="Ship", content="Shipping attracts users.", status="active", position=0, next_ids=("fw-2",))
    n2 = FlywheelNode(id="fw-2", slug="learn", title="Learn", content="Learning improves shipping.", status=None, position=1, next_ids=("fw-1",))
    fw = Flywheel(id="fw", slug="loop", title="Loop", content="The loop.", status=None, nodes=(n1, n2))
    outcome = make_node("outcome", "o")
    snap = GraphSnapshot(nodes=[outcome], flywheel=fw)
    md = context_markdown(snap, outcome)
    assert "## Flywheel Context" in md
    assert "#### Ship" in md
    assert "Next: flywheel-node.learn" in md
