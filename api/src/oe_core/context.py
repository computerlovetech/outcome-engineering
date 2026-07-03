"""Agent-facing context assembly for a node: deterministic markdown covering
vision, current strategy, related ICPs, the ancestor chain, the node itself,
its children, and the flywheel."""

from __future__ import annotations

from oe_core.model import Flywheel, GraphSnapshot, Node


def context_markdown(snapshot: GraphSnapshot, node: Node) -> str:
    ancestors = snapshot.ancestors(node)
    icps = snapshot.related_icps(node)
    children = snapshot.children(node)
    vision = snapshot.vision()
    strategy = snapshot.current_strategy()

    lines = [f"# Context: {node.ref}", "", "## Trace"]
    for ancestor in ancestors:
        lines.append(f"- {ancestor.ref}")
    lines.append(f"- {node.ref}")

    _append_ref_section(lines, "ICPs", icps)
    _append_ref_section(lines, "Children", children)

    if vision is not None and vision.id != node.id:
        _append_content_block(lines, "Vision", vision)
    if strategy is not None and strategy.id != node.id:
        _append_content_block(lines, "Current Strategy", strategy)

    if snapshot.flywheel is not None:
        lines.extend(["", "## Flywheel Context", "", flywheel_markdown(snapshot.flywheel)])

    _append_content_section(lines, "Ancestor Content", ancestors)
    _append_content_section(lines, "ICP Content", icps)
    lines.extend(["", "## Node Content", "", node.content.rstrip()])
    return "\n".join(lines)


def flywheel_markdown(flywheel: Flywheel) -> str:
    by_id = {node.id: node for node in flywheel.nodes}
    lines = [f"### Flywheel: {flywheel.title or flywheel.ref}"]
    if flywheel.status:
        lines.append(f"Status: {flywheel.status}")
    body = flywheel.content.rstrip()
    if body:
        lines.extend(["", body])
    for node in flywheel.nodes:
        next_refs = ", ".join(by_id[next_id].ref for next_id in node.next_ids if next_id in by_id)
        lines.extend(["", f"#### {node.title or node.ref}"])
        if node.status:
            lines.append(f"Status: {node.status}")
        if next_refs:
            lines.append(f"Next: {next_refs}")
        node_body = node.content.rstrip()
        if node_body:
            lines.extend(["", node_body])
    return "\n".join(lines)


def _append_ref_section(lines: list[str], title: str, nodes: list[Node]) -> None:
    if not nodes:
        return
    lines.extend(["", f"## {title}"])
    for node in nodes:
        lines.append(f"- {node.ref}")


def _append_content_block(lines: list[str], title: str, node: Node) -> None:
    lines.extend(["", f"## {title}", "", node.content.rstrip()])


def _append_content_section(lines: list[str], title: str, nodes: list[Node]) -> None:
    if not nodes:
        return
    lines.extend(["", f"## {title}"])
    for node in nodes:
        lines.extend(["", f"### {node.ref}", "", node.content.rstrip()])
