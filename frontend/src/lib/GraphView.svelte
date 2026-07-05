<script lang="ts">
	// The graph canvas: strategic overview (vision / strategy / ICPs / outcome
	// trees) + flywheel view + side detail panel with markdown editing, child
	// creation constrained by placement rules, and cascade delete.
	// Ported from the old oe-serve graph.html; the imperative SVG code is kept
	// close to the original on purpose.
	import { onMount } from 'svelte';
	import { api } from '$lib/api';
	import { renderMarkdown, stripFrontHeading, slugify } from '$lib/markdown';

	let {
		graphRef,
		shareToken = undefined
	}: { graphRef: string; shareToken?: string } = $props();

	const KIND_COLOR: Record<string, string> = {
		vision: '#d96c75',
		strategy: '#c6a15b',
		icp: '#b07cf0',
		job: '#d0679d',
		outcome: '#4f8cf7',
		opportunity: '#2bb3a3',
		solution: '#f0913a',
		'assumption-test': '#e6c34a',
		prd: '#8a94a6',
		'flywheel-node': '#6f8f46'
	};
	const NODE_W = 240,
		NODE_MIN_H = 58,
		ROW_H = 142,
		COL_W = 284;
	const TITLE_CHARS_PER_LINE = 24,
		TITLE_LINE_H = 14;
	const SVGNS = 'http://www.w3.org/2000/svg';

	/* eslint-disable @typescript-eslint/no-explicit-any */
	type N = any;

	let GRAPH: N = { nodes: [], edges: [], flywheel: null, schema: { childKinds: {} }, readOnly: true, graph: {} };
	let readOnly = $state(true);
	let graphName = $state('');
	let hasFlywheel = $state(false);
	let hasVision = $state(false);
	let mode = $state<'overview' | 'flywheel'>('overview');

	let byRef = new Map<string, N>();
	let childrenOf = new Map<string, N[]>();
	let visions: N[] = [],
		strategies: N[] = [],
		outcomes: N[] = [],
		icps: N[] = [],
		jobs: N[] = [];
	let flywheelByRef = new Map<string, N>();

	let svg: SVGSVGElement;
	let viewport: SVGGElement;
	let detail: HTMLDivElement;
	let toastEl: HTMLDivElement;

	const ui = {
		collapsed: new Set<string>(),
		selected: null as string | null,
		view: { x: 0, y: 0, k: 1 }
	};

	function buildIndexes() {
		byRef = new Map(GRAPH.nodes.map((n: N) => [n.ref, n]));
		childrenOf = new Map();
		GRAPH.nodes.forEach((n: N) => childrenOf.set(n.ref, []));
		GRAPH.nodes.forEach((n: N) => {
			if (n.parent && childrenOf.has(n.parent)) childrenOf.get(n.parent)!.push(n);
		});
		visions = GRAPH.nodes.filter((n: N) => n.kind === 'vision');
		strategies = GRAPH.nodes.filter((n: N) => n.kind === 'strategy');
		outcomes = GRAPH.nodes.filter((n: N) => n.kind === 'outcome');
		icps = GRAPH.nodes.filter((n: N) => n.kind === 'icp');
		jobs = GRAPH.nodes.filter((n: N) => n.kind === 'job');
		flywheelByRef = new Map(
			((GRAPH.flywheel && GRAPH.flywheel.nodes) || []).map((n: N) => [n.ref, { ...n, kind: 'flywheel-node' }])
		);
	}
	function childKinds(kind: string): string[] {
		return GRAPH.schema?.childKinds?.[kind] || [];
	}
	function apiCall(method: string, path: string, body?: unknown) {
		return api(method, path, body, shareToken ? { shareToken } : {});
	}

	function el(tag: string, attrs: Record<string, string | number> = {}, children: Node[] = []) {
		const node = document.createElementNS(SVGNS, tag);
		for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, String(v));
		for (const c of children) node.appendChild(c);
		return node;
	}
	function clear(node: Element) {
		while (node.firstChild) node.removeChild(node.firstChild);
	}

	// ---- node + edge primitives ----------------------------------------------
	function wrapTitle(title: string): string[] {
		const words = String(title || '').split(/\s+/).filter(Boolean);
		const lines: string[] = [];
		let line = '';
		words.forEach((word) => {
			while (word.length > TITLE_CHARS_PER_LINE) {
				if (line) {
					lines.push(line);
					line = '';
				}
				lines.push(word.slice(0, TITLE_CHARS_PER_LINE));
				word = word.slice(TITLE_CHARS_PER_LINE);
			}
			if (!line) {
				line = word;
				return;
			}
			if ((line + ' ' + word).length <= TITLE_CHARS_PER_LINE) line += ' ' + word;
			else {
				lines.push(line);
				line = word;
			}
		});
		if (line) lines.push(line);
		return lines.length ? lines : [''];
	}
	function nodeHeight(n: N): number {
		const contentH = 32 + wrapTitle(n.title).length * TITLE_LINE_H + (n.status ? 12 : 0);
		return Math.max(NODE_MIN_H, contentH);
	}
	function drawNode(n: N, x: number, y: number, opts: { toggle?: boolean; onClick?: (n: N) => void } = {}) {
		const color = KIND_COLOR[n.kind] || '#888';
		const h = nodeHeight(n);
		const top = -h / 2;
		const left = -NODE_W / 2;
		const g = el('g', {
			class: 'node' + (ui.selected === n.ref ? ' selected' : ''),
			transform: `translate(${x},${y})`
		});
		g.appendChild(el('rect', { class: 'fill', x: left + 2, y: top + 2, width: NODE_W - 4, height: h - 4, rx: 6, fill: color }));
		g.appendChild(el('rect', { class: 'box', x: left, y: top, width: NODE_W, height: h, rx: 7, stroke: color }));
		g.appendChild(
			el('path', {
				class: 'stripe',
				d: `M ${left + 8} ${top + 6} L ${left + 8} ${h / 2 - 7}`,
				stroke: color,
				'stroke-width': 5,
				'stroke-linecap': 'round'
			})
		);
		const kindText = el('text', { class: 'kind', x: left + 16, y: top + 15 });
		kindText.textContent = n.kind;
		g.appendChild(kindText);
		const label = el('text', { class: 'label', x: left + 16, y: top + 34 });
		wrapTitle(n.title).forEach((line, i) => {
			const tspan = el('tspan', { x: left + 16, dy: i === 0 ? 0 : TITLE_LINE_H });
			tspan.textContent = line;
			label.appendChild(tspan);
		});
		g.appendChild(label);
		if (n.status) {
			const s = el('text', { class: 'status', x: left + 16, y: h / 2 - 8 });
			s.textContent = n.status;
			g.appendChild(s);
		}
		g.addEventListener('click', (e) => {
			e.stopPropagation();
			(opts.onClick || onNodeClick)(n);
		});
		viewport.appendChild(g);
		if (opts.toggle) {
			const t = el('g', { class: 'toggle', transform: `translate(${x},${y + h / 2 + 12})` });
			t.appendChild(el('circle', { r: 10 }));
			const sign = el('text', {});
			sign.textContent = ui.collapsed.has(n.ref) ? '+' : '−';
			t.appendChild(sign);
			t.addEventListener('click', (e) => {
				e.stopPropagation();
				toggleCollapse(n.ref);
			});
			viewport.appendChild(t);
		}
	}

	type Pos = { x: number; y: number; h?: number; angle?: number; radius?: number; index?: number };
	function edgePath(a: Pos, b: Pos, type: string) {
		const my = (a.y + b.y) / 2;
		const wobble = sketchOffset(a, b);
		const d = `M ${a.x} ${a.y + (a.h || NODE_MIN_H) / 2} C ${a.x + wobble.a} ${my + wobble.b}, ${b.x + wobble.c} ${my - wobble.a}, ${b.x} ${b.y - (b.h || NODE_MIN_H) / 2}`;
		return el('path', { class: 'edge' + (type === 'icp' || type === 'job' ? ' ' + type : ''), d });
	}
	function sketchOffset(a: Pos, b: Pos) {
		const seed = Math.sin(a.x * 12.9898 + a.y * 78.233 + b.x * 37.719 + b.y * 11.131) * 43758.5453;
		const f = seed - Math.floor(seed);
		return { a: (f - 0.5) * 16, b: (((f * 7) % 1) - 0.5) * 12, c: (((f * 13) % 1) - 0.5) * 14 };
	}

	// ---- overview ---------------------------------------------------------------
	function renderOverview() {
		clear(viewport);
		const pos = new Map<string, Pos>();
		let cursor = 0;

		function layoutTree(n: N, depth: number) {
			const kids = ui.collapsed.has(n.ref) ? [] : childrenOf.get(n.ref) || [];
			const y = depth * ROW_H;
			if (!kids.length) {
				pos.set(n.ref, { x: cursor * COL_W, y, h: nodeHeight(n) });
				cursor++;
				return;
			}
			kids.forEach((c) => layoutTree(c, depth + 1));
			const xs = kids.map((c) => pos.get(c.ref)!.x);
			pos.set(n.ref, { x: (Math.min(...xs) + Math.max(...xs)) / 2, y, h: nodeHeight(n) });
		}

		outcomes.forEach((o) => layoutTree(o, 3));
		const graphXs = outcomes.map((o) => pos.get(o.ref)!.x);
		const minX = graphXs.length ? Math.min(...graphXs) : 0;
		const maxX = graphXs.length ? Math.max(...graphXs) : 0;
		const centerX = (minX + maxX) / 2;
		const visionX = spread(visions.length, COL_W * 1.2).map((x) => x + centerX);
		const strategyX = spread(strategies.length, COL_W * 1.2).map((x) => x + centerX);
		const customerRowX = spread(icps.length + jobs.length, COL_W).map((x) => x + centerX);
		const icpX = customerRowX.slice(0, icps.length);
		const jobX = customerRowX.slice(icps.length);
		const visionY = 0,
			strategyY = ROW_H * 0.95,
			icpY = ROW_H * 1.9;
		visions.forEach((vision, i) => pos.set(vision.ref, { x: visionX[i], y: visionY, h: nodeHeight(vision) }));
		strategies.forEach((strategy, i) => pos.set(strategy.ref, { x: strategyX[i], y: strategyY, h: nodeHeight(strategy) }));
		icps.forEach((icp, i) => pos.set(icp.ref, { x: icpX[i], y: icpY, h: nodeHeight(icp) }));
		jobs.forEach((job, i) => pos.set(job.ref, { x: jobX[i], y: icpY, h: nodeHeight(job) }));

		visions.forEach((vision) => {
			const targets = strategies.length ? strategies : outcomes;
			targets.forEach((target) => {
				if (pos.has(target.ref)) viewport.appendChild(edgePath(pos.get(vision.ref)!, pos.get(target.ref)!, 'structural'));
			});
		});
		strategies.forEach((strategy) => {
			outcomes.forEach((o) => viewport.appendChild(edgePath(pos.get(strategy.ref)!, pos.get(o.ref)!, 'structural')));
		});
		GRAPH.edges
			.filter((e: N) => e.type === 'structural')
			.forEach((e: N) => {
				if (pos.has(e.source) && pos.has(e.target)) viewport.appendChild(edgePath(pos.get(e.source)!, pos.get(e.target)!, 'structural'));
			});
		GRAPH.edges
			// job → ICP references share the customer-context row; the detail panel
			// shows them as chips instead of drawing a flat same-row edge.
			.filter((e: N) => (e.type === 'icp' || e.type === 'job') && byRef.get(e.source)?.kind !== 'job')
			.forEach((e: N) => {
				if (pos.has(e.source) && pos.has(e.target)) viewport.appendChild(edgePath(pos.get(e.target)!, pos.get(e.source)!, e.type));
			});

		if (visions.length) addBandLabel('vision', visionX, visionY);
		if (strategies.length) addBandLabel('strategy', strategyX, strategyY);
		if (icps.length) addBandLabel('ideal customer profiles', icpX, icpY);
		if (jobs.length) addBandLabel('jobs', jobX, icpY);
		if (outcomes.length) addBandLabel('Outcome Graph', [minX], ROW_H * 3);
		visions.forEach((vision) => drawNode(vision, pos.get(vision.ref)!.x, pos.get(vision.ref)!.y));
		strategies.forEach((strategy) => drawNode(strategy, pos.get(strategy.ref)!.x, pos.get(strategy.ref)!.y));
		icps.forEach((icp) => drawNode(icp, pos.get(icp.ref)!.x, pos.get(icp.ref)!.y));
		jobs.forEach((job) => drawNode(job, pos.get(job.ref)!.x, pos.get(job.ref)!.y));
		outcomes.forEach((o) => drawFullGraphNode(o, pos));
	}

	function drawFullGraphNode(n: N, pos: Map<string, Pos>) {
		const p = pos.get(n.ref)!;
		const kids = childrenOf.get(n.ref) || [];
		drawNode(n, p.x, p.y, { toggle: kids.length > 0 });
		if (!ui.collapsed.has(n.ref)) kids.forEach((child) => drawFullGraphNode(child, pos));
	}

	function addBandLabel(text: string, xs: number[], y: number) {
		if (!xs.length) return;
		const t = el('text', { class: 'band-label', x: Math.min(...xs) - NODE_W / 2, y: y - NODE_MIN_H / 2 - 18 });
		t.textContent = text;
		viewport.appendChild(t);
	}
	function spread(count: number, gap: number): number[] {
		const xs: number[] = [];
		const start = -((count - 1) * gap) / 2;
		for (let i = 0; i < count; i++) xs.push(start + i * gap);
		return xs;
	}

	// ---- flywheel ---------------------------------------------------------------
	function renderFlywheel() {
		clear(viewport);
		const fw = GRAPH.flywheel;
		if (!fw || !fw.nodes || !fw.nodes.length) {
			if (fw) showFlywheelDetail();
			return;
		}
		const nodes = orderFlywheelNodes(fw.nodes.map((n: N) => ({ ...n, kind: 'flywheel-node' })));
		const radius = Math.max(230, nodes.length * 62);
		const step = (2 * Math.PI) / nodes.length;
		const pos = new Map<string, Pos>();
		nodes.forEach((n: N, i: number) => {
			const angle = -Math.PI / 2 + i * step;
			pos.set(n.ref, { x: Math.cos(angle) * radius, y: Math.sin(angle) * radius, h: nodeHeight(n), angle, radius, index: i });
		});
		nodes.forEach((source: N) => {
			(source.next || []).forEach((targetRef: string) => {
				const target = nodes.find((n: N) => n.ref === targetRef);
				if (!target || !pos.has(source.ref) || !pos.has(target.ref)) return;
				drawFlywheelEdge(source, target, pos.get(source.ref)!, pos.get(target.ref)!);
			});
		});
		nodes.forEach((n: N) => drawNode(n, pos.get(n.ref)!.x, pos.get(n.ref)!.y, { onClick: onFlywheelNodeClick }));
	}

	function orderFlywheelNodes(nodes: N[]): N[] {
		if (!nodes.length) return nodes;
		const byNodeRef = new Map(nodes.map((n) => [n.ref, n]));
		const pointedAt = new Set(nodes.flatMap((n) => n.next || []));
		const start = nodes.find((n) => !pointedAt.has(n.ref)) || nodes[0];
		const ordered: N[] = [];
		const seen = new Set<string>();
		let current: N | undefined = start;
		while (current && !seen.has(current.ref)) {
			ordered.push(current);
			seen.add(current.ref);
			current = byNodeRef.get((current.next || [])[0]);
		}
		nodes.forEach((n) => {
			if (!seen.has(n.ref)) ordered.push(n);
		});
		return ordered;
	}

	function drawFlywheelEdge(source: N, target: N, a: Pos, b: Pos) {
		const count = GRAPH.flywheel.nodes.length;
		const step = (Math.PI * 2) / Math.max(1, count);
		const trim = Math.min(step * 0.26, 0.28);
		const clockwise = (b.index! - a.index! + count) % count <= 1;
		const startAngle = a.angle! + (clockwise ? trim : -trim);
		const endAngle = b.angle! - (clockwise ? trim : -trim);
		const edgeRadius = a.radius! * 0.88;
		const start = { x: Math.cos(startAngle) * edgeRadius, y: Math.sin(startAngle) * edgeRadius };
		const end = { x: Math.cos(endAngle) * edgeRadius, y: Math.sin(endAngle) * edgeRadius };
		const path = el('path', {
			class: 'edge flywheel',
			d: `M ${start.x} ${start.y} A ${edgeRadius} ${edgeRadius} 0 0 ${clockwise ? 1 : 0} ${end.x} ${end.y}`
		});
		path.addEventListener('click', (e) => {
			e.stopPropagation();
			onFlywheelNodeClick(source);
		});
		viewport.appendChild(path);
	}

	// ---- interaction ------------------------------------------------------------
	function onNodeClick(n: N) {
		ui.selected = n.ref;
		showDetail(n);
		render();
	}
	function onFlywheelNodeClick(n: N) {
		ui.selected = n.ref;
		showFlywheelNodeDetail(n);
		render();
	}
	function enterFlywheel() {
		mode = 'flywheel';
		ui.selected = null;
		render({ fitView: true });
		showFlywheelDetail();
	}
	function goOverview() {
		mode = 'overview';
		ui.selected = null;
		render({ fitView: true });
		clearDetail();
	}
	function toggleCollapse(ref: string) {
		if (ui.collapsed.has(ref)) ui.collapsed.delete(ref);
		else ui.collapsed.add(ref);
		render({ fitView: true });
	}

	function render({ fitView = false }: { fitView?: boolean } = {}) {
		if (!viewport) return;
		if (mode === 'flywheel') renderFlywheel();
		else renderOverview();
		if (fitView) fit();
		else applyView();
	}

	// ---- detail panel -----------------------------------------------------------
	function clearHtml(node: Element) {
		while (node.firstChild) node.removeChild(node.firstChild);
	}
	function clearDetail() {
		detail.className = 'gv-detail empty';
		detail.textContent = 'Select a node to see its content.';
	}
	function panelStart(): HTMLDivElement {
		detail.className = 'gv-detail';
		clearHtml(detail);
		return detail;
	}
	function addPill(d: HTMLElement, text: string, color?: string) {
		const pill = document.createElement('span');
		pill.className = 'pill';
		if (color) {
			pill.style.color = color;
			pill.style.borderColor = color;
		}
		pill.textContent = text;
		d.appendChild(pill);
	}
	function addTitle(d: HTMLElement, title: string, id: string) {
		const h = document.createElement('h1');
		h.textContent = title;
		d.appendChild(h);
		const idEl = document.createElement('div');
		idEl.className = 'id';
		idEl.textContent = id;
		d.appendChild(idEl);
	}
	function addMarkdown(d: HTMLElement, body: string) {
		const md = document.createElement('div');
		md.className = 'md';
		md.innerHTML = renderMarkdown(stripFrontHeading(body));
		d.appendChild(md);
	}
	function addChips(d: HTMLElement, label: string, refs: string[], lookup: Map<string, N>, onChipClick: (n: N) => void) {
		if (!refs.length) return;
		const wrap = document.createElement('div');
		wrap.className = 'served';
		const lbl = document.createElement('div');
		lbl.style.color = 'var(--muted)';
		lbl.style.fontSize = '12px';
		lbl.textContent = label;
		wrap.appendChild(lbl);
		refs.forEach((ref) => {
			const chip = document.createElement('span');
			chip.className = 'chip';
			const target = lookup.get(ref);
			chip.textContent = target ? target.title : ref;
			chip.onclick = () => {
				const t = lookup.get(ref);
				if (t) onChipClick(t);
			};
			wrap.appendChild(chip);
		});
		d.appendChild(wrap);
	}
	function button(text: string, cls: string, onclick: () => void): HTMLButtonElement {
		const b = document.createElement('button');
		b.className = cls;
		b.textContent = text;
		b.onclick = onclick;
		return b;
	}

	function showDetail(n: N) {
		const d = panelStart();
		addPill(d, n.kind, KIND_COLOR[n.kind]);
		if (n.kind === 'strategy' && n.starts) addPill(d, `${n.starts} → ${n.ends}`);
		addTitle(d, n.title, n.ref);
		if (n.kind === 'icp' || n.kind === 'job') {
			addChips(d, 'Serves', n.servedBy || [], byRef, onNodeClick);
		}
		if (n.kind === 'job') {
			addChips(d, 'ICPs', n.icps || [], byRef, onNodeClick);
		} else {
			addChips(d, 'ICPs served', n.icps || [], byRef, onNodeClick);
			addChips(d, 'Jobs', n.jobs || [], byRef, onNodeClick);
		}

		if (!readOnly) {
			const actions = document.createElement('div');
			actions.className = 'actions';
			actions.appendChild(button('Edit', 'btn primary', () => showEditor(n)));
			childKinds(n.kind).forEach((ck: string) => {
				actions.appendChild(button('+ ' + ck, 'btn', () => showCreateForm(ck, n.ref)));
			});
			if (n.deletable !== false) {
				actions.appendChild(button('Delete', 'btn danger', () => deleteNode(n)));
			}
			d.appendChild(actions);
		}
		addMarkdown(d, n.content);
	}

	function showFlywheelDetail() {
		const fw = GRAPH.flywheel;
		if (!fw) {
			clearDetail();
			return;
		}
		const d = panelStart();
		addPill(d, 'flywheel', KIND_COLOR['flywheel-node']);
		if (fw.status) addPill(d, fw.status);
		addTitle(d, fw.title, fw.ref);
		if (!readOnly) {
			const actions = document.createElement('div');
			actions.className = 'actions';
			actions.appendChild(button('+ node', 'btn', () => showFlywheelNodeForm()));
			actions.appendChild(
				button('Delete flywheel', 'btn danger', async () => {
					if (!confirm('Delete the flywheel and all its nodes?')) return;
					const res = await apiCall('DELETE', `/api/graphs/${graphRef}/flywheel`);
					if (res.ok) {
						toast('Deleted flywheel', 'ok');
						mode = 'overview';
						await reload();
						clearDetail();
					} else toast(res.error || 'Delete failed', 'error');
				})
			);
			d.appendChild(actions);
		}
		addMarkdown(d, fw.content);
	}

	function showFlywheelNodeDetail(n: N) {
		const d = panelStart();
		addPill(d, 'flywheel node', KIND_COLOR['flywheel-node']);
		if (n.status) addPill(d, n.status);
		addTitle(d, n.title, n.ref);
		addChips(d, 'Next', n.next || [], flywheelByRef, onFlywheelNodeClick);
		if (!readOnly) {
			const actions = document.createElement('div');
			actions.className = 'actions';
			actions.appendChild(button('Edit', 'btn primary', () => showFlywheelNodeEditor(n)));
			actions.appendChild(
				button('Delete', 'btn danger', async () => {
					if (!confirm(`Delete flywheel node "${n.title}"?`)) return;
					const res = await apiCall('DELETE', `/api/graphs/${graphRef}/flywheel/nodes/${encodeURIComponent(n.slug)}`);
					if (res.ok) {
						toast('Deleted', 'ok');
						ui.selected = null;
						await reload();
						showFlywheelDetail();
					} else toast(res.error || 'Delete failed', 'error');
				})
			);
			d.appendChild(actions);
		}
		addMarkdown(d, n.content);
	}

	// ---- editing / creating / deleting -------------------------------------------
	function labeled(parent: HTMLElement, text: string): void {
		const lbl = document.createElement('label');
		lbl.textContent = text;
		parent.appendChild(lbl);
	}

	function refCheckRow(parent: HTMLElement, target: N, selected: string[]): HTMLInputElement {
		const row = document.createElement('div');
		row.className = 'check-row';
		const check = document.createElement('input');
		check.type = 'checkbox';
		check.value = target.ref;
		check.checked = selected.includes(target.ref);
		const lbl = document.createElement('span');
		lbl.textContent = target.title;
		row.appendChild(check);
		row.appendChild(lbl);
		parent.appendChild(row);
		return check;
	}

	function showEditor(n: N) {
		const d = panelStart();
		addTitle(d, 'Edit ' + n.title, n.ref);
		const ed = document.createElement('div');
		ed.className = 'editor';

		labeled(ed, 'Title');
		const titleInput = document.createElement('input');
		titleInput.className = 'field';
		titleInput.value = n.title;
		ed.appendChild(titleInput);

		let startsInput: HTMLInputElement | null = null;
		let endsInput: HTMLInputElement | null = null;
		if (n.kind === 'strategy') {
			labeled(ed, 'Starts');
			startsInput = document.createElement('input');
			startsInput.className = 'field';
			startsInput.type = 'date';
			startsInput.value = n.starts || '';
			ed.appendChild(startsInput);
			labeled(ed, 'Ends');
			endsInput = document.createElement('input');
			endsInput.className = 'field';
			endsInput.type = 'date';
			endsInput.value = n.ends || '';
			ed.appendChild(endsInput);
		}

		const icpChecks: HTMLInputElement[] = [];
		if ((n.kind === 'outcome' || n.kind === 'opportunity' || n.kind === 'job') && icps.length) {
			labeled(ed, n.kind === 'job' ? 'ICPs with this job' : 'ICPs served');
			icps.forEach((icp) => icpChecks.push(refCheckRow(ed, icp, n.icps || [])));
		}

		const jobChecks: HTMLInputElement[] = [];
		if ((n.kind === 'outcome' || n.kind === 'opportunity') && jobs.length) {
			labeled(ed, 'Jobs');
			jobs.forEach((job) => jobChecks.push(refCheckRow(ed, job, n.jobs || [])));
		}

		labeled(ed, 'Content (markdown)');
		const ta = document.createElement('textarea');
		ta.className = 'marker';
		ta.value = n.content + '\n';
		ed.appendChild(ta);

		const actions = document.createElement('div');
		actions.className = 'actions';
		const save = button('Save', 'btn primary', async () => {
			save.disabled = true;
			const body: Record<string, unknown> = {
				version: n.version,
				title: titleInput.value,
				content: ta.value.replace(/\n$/, '')
			};
			if (startsInput && startsInput.value) body.starts = startsInput.value;
			if (endsInput && endsInput.value) body.ends = endsInput.value;
			if (icpChecks.length) body.icps = icpChecks.filter((c) => c.checked).map((c) => c.value);
			if (jobChecks.length) body.jobs = jobChecks.filter((c) => c.checked).map((c) => c.value);
			const res = await apiCall('PATCH', `/api/graphs/${graphRef}/nodes/${encodeURIComponent(n.ref)}`, body);
			if (res.ok) {
				toast('Saved', 'ok');
				await reload(n.ref);
				const updated = byRef.get(n.ref);
				if (updated) showDetail(updated);
			} else if (res.status === 409) {
				save.disabled = false;
				toast('Conflict: ' + (res.error || 'the node changed while you edited'), 'error');
			} else {
				save.disabled = false;
				toast(res.error || 'Save failed', 'error');
			}
		});
		actions.appendChild(save);
		actions.appendChild(
			button('Cancel', 'btn', () => {
				const t = byRef.get(n.ref);
				if (t) showDetail(t);
				else clearDetail();
			})
		);
		ed.appendChild(actions);
		d.appendChild(ed);
		ta.focus();
	}

	function showCreateForm(kind: string, under: string | null) {
		const d = panelStart();
		addTitle(d, 'New ' + kind, under ? 'under ' + under : 'at the graph root');
		const form = document.createElement('div');
		form.className = 'form';
		labeled(form, 'Title');
		const title = document.createElement('input');
		title.placeholder = kind + ' title';
		form.appendChild(title);
		const slugPreview = document.createElement('div');
		slugPreview.className = 'slug-preview';
		form.appendChild(slugPreview);
		title.oninput = () => {
			slugPreview.textContent = title.value ? 'slug: ' + slugify(title.value) : '';
		};

		let startsInput: HTMLInputElement | null = null;
		let endsInput: HTMLInputElement | null = null;
		if (kind === 'strategy') {
			labeled(form, 'Starts');
			startsInput = document.createElement('input');
			startsInput.type = 'date';
			form.appendChild(startsInput);
			labeled(form, 'Ends');
			endsInput = document.createElement('input');
			endsInput.type = 'date';
			form.appendChild(endsInput);
		}

		const actions = document.createElement('div');
		actions.className = 'actions';
		const create = button('Create', 'btn primary', async () => {
			const slug = slugify(title.value);
			if (!slug) {
				toast('Enter a title', 'error');
				return;
			}
			create.disabled = true;
			const body: Record<string, unknown> = { kind, slug, title: title.value, under: under || null };
			if (startsInput?.value) body.starts = startsInput.value;
			if (endsInput?.value) body.ends = endsInput.value;
			const res = await apiCall('POST', `/api/graphs/${graphRef}/nodes`, body);
			if (res.ok) {
				const newRef = (res.data as N).node.ref;
				toast('Created ' + newRef, 'ok');
				await reload(newRef);
				const created = byRef.get(newRef);
				if (created) {
					ui.selected = created.ref;
					showDetail(created);
					render();
				}
			} else {
				create.disabled = false;
				toast(res.error || 'Create failed', 'error');
			}
		});
		actions.appendChild(create);
		actions.appendChild(
			button('Cancel', 'btn', () => {
				const t = under ? byRef.get(under) : null;
				if (t) showDetail(t);
				else clearDetail();
			})
		);
		form.appendChild(actions);
		d.appendChild(form);
		title.focus();
	}

	async function deleteNode(n: N) {
		const kids = childrenOf.get(n.ref) || [];
		let cascade = false;
		if (kids.length) {
			if (!confirm(`${n.title} has ${kids.length} child node(s). Delete it and its entire subtree?`)) return;
			cascade = true;
		} else if (!confirm(`Delete ${n.title}?`)) {
			return;
		}
		const path = `/api/graphs/${graphRef}/nodes/${encodeURIComponent(n.ref)}` + (cascade ? '?cascade=true' : '');
		const res = await apiCall('DELETE', path);
		if (res.ok) {
			toast('Deleted ' + n.ref, 'ok');
			ui.selected = null;
			await reload();
			clearDetail();
		} else toast(res.error || 'Delete failed', 'error');
	}

	// ---- flywheel editing --------------------------------------------------------
	async function createFlywheel() {
		const title = prompt('Flywheel title', 'Flywheel');
		if (!title) return;
		const res = await apiCall('PUT', `/api/graphs/${graphRef}/flywheel`, {
			slug: slugify(title) || 'flywheel',
			title,
			content: ''
		});
		if (res.ok) {
			toast('Flywheel created', 'ok');
			await reload();
			enterFlywheel();
		} else toast(res.error || 'Create failed', 'error');
	}

	function flywheelNodeChecklist(form: HTMLElement, selected: string[], excludeRef?: string): HTMLInputElement[] {
		const checks: HTMLInputElement[] = [];
		const nodes = (GRAPH.flywheel?.nodes || []).filter((n: N) => n.ref !== excludeRef);
		if (!nodes.length) return checks;
		labeled(form, 'Next steps');
		nodes.forEach((n: N) => {
			const row = document.createElement('div');
			row.className = 'check-row';
			const check = document.createElement('input');
			check.type = 'checkbox';
			check.value = n.slug;
			check.checked = selected.includes(n.ref);
			checks.push(check);
			const lbl = document.createElement('span');
			lbl.textContent = n.title;
			row.appendChild(check);
			row.appendChild(lbl);
			form.appendChild(row);
		});
		return checks;
	}

	function showFlywheelNodeForm() {
		const d = panelStart();
		addTitle(d, 'New flywheel node', GRAPH.flywheel.ref);
		const form = document.createElement('div');
		form.className = 'form';
		labeled(form, 'Title');
		const title = document.createElement('input');
		form.appendChild(title);
		labeled(form, 'Why it creates the next step (markdown)');
		const ta = document.createElement('textarea');
		ta.className = 'marker';
		ta.style.minHeight = '140px';
		form.appendChild(ta);
		const checks = flywheelNodeChecklist(form, []);
		const actions = document.createElement('div');
		actions.className = 'actions';
		const create = button('Create', 'btn primary', async () => {
			const slug = slugify(title.value);
			if (!slug) {
				toast('Enter a title', 'error');
				return;
			}
			create.disabled = true;
			const res = await apiCall('POST', `/api/graphs/${graphRef}/flywheel/nodes`, {
				slug,
				title: title.value,
				content: ta.value,
				next: checks.filter((c) => c.checked).map((c) => c.value),
				position: (GRAPH.flywheel?.nodes || []).length
			});
			if (res.ok) {
				toast('Created', 'ok');
				await reload();
				showFlywheelDetail();
				render({ fitView: true });
			} else {
				create.disabled = false;
				toast(res.error || 'Create failed', 'error');
			}
		});
		actions.appendChild(create);
		actions.appendChild(button('Cancel', 'btn', () => showFlywheelDetail()));
		form.appendChild(actions);
		d.appendChild(form);
		title.focus();
	}

	function showFlywheelNodeEditor(n: N) {
		const d = panelStart();
		addTitle(d, 'Edit ' + n.title, n.ref);
		const form = document.createElement('div');
		form.className = 'form';
		labeled(form, 'Title');
		const title = document.createElement('input');
		title.value = n.title;
		form.appendChild(title);
		labeled(form, 'Status');
		const status = document.createElement('input');
		status.value = n.status || '';
		form.appendChild(status);
		labeled(form, 'Content (markdown)');
		const ta = document.createElement('textarea');
		ta.className = 'marker';
		ta.style.minHeight = '160px';
		ta.value = n.content;
		form.appendChild(ta);
		const checks = flywheelNodeChecklist(form, n.next || [], n.ref);
		const actions = document.createElement('div');
		actions.className = 'actions';
		const save = button('Save', 'btn primary', async () => {
			save.disabled = true;
			const res = await apiCall('PATCH', `/api/graphs/${graphRef}/flywheel/nodes/${encodeURIComponent(n.slug)}`, {
				title: title.value,
				status: status.value,
				content: ta.value,
				next: checks.filter((c) => c.checked).map((c) => c.value)
			});
			if (res.ok) {
				toast('Saved', 'ok');
				await reload();
				const updated = flywheelByRef.get(n.ref);
				if (updated) showFlywheelNodeDetail(updated);
				render();
			} else {
				save.disabled = false;
				toast(res.error || 'Save failed', 'error');
			}
		});
		actions.appendChild(save);
		actions.appendChild(button('Cancel', 'btn', () => showFlywheelNodeDetail(n)));
		form.appendChild(actions);
		d.appendChild(form);
	}

	// ---- toast --------------------------------------------------------------------
	let toastTimer: ReturnType<typeof setTimeout> | null = null;
	function toast(msg: string, kind?: string) {
		toastEl.textContent = msg;
		toastEl.className = 'gv-toast show' + (kind ? ' ' + kind : '');
		if (toastTimer) clearTimeout(toastTimer);
		toastTimer = setTimeout(() => {
			toastEl.className = 'gv-toast';
		}, 3200);
	}

	// ---- pan / zoom ------------------------------------------------------------------
	function applyView() {
		viewport.setAttribute('transform', `translate(${ui.view.x},${ui.view.y}) scale(${ui.view.k})`);
	}
	function fit() {
		const bb = viewport.getBBox();
		if (!bb.width || !bb.height) {
			ui.view = { x: 0, y: 0, k: 1 };
			applyView();
			return;
		}
		const rect = svg.getBoundingClientRect();
		const pad = 60;
		const k = Math.min((rect.width - pad) / bb.width, (rect.height - pad) / bb.height, 1.3);
		ui.view.k = k;
		ui.view.x = rect.width / 2 - (bb.x + bb.width / 2) * k;
		ui.view.y = rect.height / 2 - (bb.y + bb.height / 2) * k;
		applyView();
	}

	function setupInteraction() {
		svg.addEventListener(
			'wheel',
			(e) => {
				e.preventDefault();
				const rect = svg.getBoundingClientRect();
				const mx = e.clientX - rect.left,
					my = e.clientY - rect.top;
				const factor = Math.exp(-e.deltaY * 0.0012);
				const nk = Math.min(Math.max(ui.view.k * factor, 0.15), 3);
				const r = nk / ui.view.k;
				ui.view.x = mx - (mx - ui.view.x) * r;
				ui.view.y = my - (my - ui.view.y) * r;
				ui.view.k = nk;
				applyView();
			},
			{ passive: false }
		);
		let dragging = false;
		let last: { x: number; y: number } | null = null;
		svg.addEventListener('mousedown', (e) => {
			dragging = true;
			last = { x: e.clientX, y: e.clientY };
			svg.classList.add('panning');
		});
		window.addEventListener('mousemove', (e) => {
			if (!dragging || !last) return;
			ui.view.x += e.clientX - last.x;
			ui.view.y += e.clientY - last.y;
			last = { x: e.clientX, y: e.clientY };
			applyView();
		});
		window.addEventListener('mouseup', () => {
			dragging = false;
			svg.classList.remove('panning');
		});
		svg.addEventListener('click', () => {
			ui.selected = null;
			render();
		});
		window.addEventListener('resize', () => applyView());
	}

	// ---- data loading -----------------------------------------------------------------
	async function reload(selectRef?: string) {
		const res = await apiCall('GET', `/api/graphs/${graphRef}/overview`);
		if (!res.ok) {
			toast(res.error || 'Failed to load graph', 'error');
			return;
		}
		GRAPH = res.data;
		buildIndexes();
		readOnly = !!GRAPH.readOnly;
		graphName = GRAPH.graph?.name || graphRef;
		hasFlywheel = !!GRAPH.flywheel;
		hasVision = visions.length > 0;
		if (mode === 'flywheel' && !GRAPH.flywheel) mode = 'overview';
		if (ui.selected && mode !== 'flywheel' && !byRef.has(ui.selected)) ui.selected = null;
		if (selectRef && byRef.has(selectRef)) ui.selected = selectRef;
		render({ fitView: true });
	}

	onMount(() => {
		setupInteraction();
		clearDetail();
		reload();
	});
</script>

<div class="gv-app">
	<header class="gv-header">
		{#if !shareToken}
			<span class="crumbs"><a href="/graphs">graphs</a></span>
		{/if}
		<span class="title">{graphName || graphRef}</span>
		<span class="crumbs">
			{#if mode === 'flywheel'}
				· <a onclick={goOverview} href={'#overview'}>overview</a> / flywheel
			{:else}
				· overview
			{/if}
		</span>
		<span class="spacer"></span>
		{#if !readOnly}
			<button class="btn" onclick={() => showCreateForm('outcome', null)}>+ Outcome</button>
			<button class="btn" onclick={() => showCreateForm('icp', null)}>+ ICP</button>
			<button class="btn" onclick={() => showCreateForm('job', null)}>+ Job</button>
			<button class="btn" onclick={() => showCreateForm('strategy', null)}>+ Strategy</button>
			{#if !hasVision}
				<button class="btn" onclick={() => showCreateForm('vision', null)}>+ Vision</button>
			{/if}
			{#if !hasFlywheel}
				<button class="btn" onclick={createFlywheel}>+ Flywheel</button>
			{/if}
		{/if}
		{#if hasFlywheel}
			<button class="btn" onclick={enterFlywheel} disabled={mode === 'flywheel'}>Flywheel</button>
		{/if}
		<button class="btn" onclick={goOverview} disabled={mode === 'overview'}>Overview</button>
		<button class="btn" onclick={() => fit()}>Fit</button>
		{#if !shareToken && !readOnly}
			<a class="btn" style="text-decoration: none" href={`/graphs/${graphRef}/settings`}>Share</a>
		{/if}
	</header>
	<div class="gv-main">
		<div class="gv-canvas-wrap">
			<svg bind:this={svg}>
				<defs>
					<filter id="sketch">
						<feTurbulence type="fractalNoise" baseFrequency="0.035" numOctaves="1" seed="8" result="noise" />
						<feDisplacementMap in="SourceGraphic" in2="noise" scale="0.45" />
					</filter>
					<marker id="arrow" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto" markerUnits="strokeWidth">
						<path d="M0,0 L0,6 L8,3 z" fill="#6f8f46"></path>
					</marker>
				</defs>
				<g bind:this={viewport}></g>
			</svg>
			<div class="gv-hint">scroll to zoom · drag to pan · click any node to inspect</div>
			<div class="gv-toast" bind:this={toastEl}></div>
		</div>
		<div class="gv-detail empty" bind:this={detail}>Select a node to see its content.</div>
	</div>
</div>
