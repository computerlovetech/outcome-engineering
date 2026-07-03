<script lang="ts">
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';
	import { api, clearToken } from '$lib/api';
	import { slugify } from '$lib/markdown';

	interface GraphInfo {
		id: string;
		slug: string;
		name: string;
		role: string;
	}

	let graphs = $state<GraphInfo[]>([]);
	let loading = $state(true);
	let error = $state('');
	let newName = $state('');

	onMount(load);

	async function load() {
		const result = await api<{ graphs: GraphInfo[] }>('GET', '/api/graphs');
		if (!result.ok) {
			if (result.status === 401) {
				goto('/');
				return;
			}
			error = result.error ?? 'Failed to load graphs';
		} else {
			graphs = result.data.graphs;
		}
		loading = false;
	}

	async function createGraph() {
		error = '';
		const slug = slugify(newName);
		if (!slug) {
			error = 'Enter a graph name.';
			return;
		}
		const result = await api('POST', '/api/graphs', { slug, name: newName.trim() });
		if (!result.ok) {
			error = result.error ?? 'Create failed';
			return;
		}
		newName = '';
		goto(`/graphs/${slug}`);
	}

	async function renameGraph(graph: GraphInfo) {
		const name = prompt('New name', graph.name);
		if (!name || name === graph.name) return;
		const result = await api('PATCH', `/api/graphs/${graph.slug}`, { name });
		if (!result.ok) {
			error = result.error ?? 'Rename failed';
			return;
		}
		await load();
	}

	async function deleteGraph(graph: GraphInfo) {
		if (!confirm(`Delete graph "${graph.name}" and everything in it? This cannot be undone.`)) return;
		const result = await api('DELETE', `/api/graphs/${graph.slug}`);
		if (!result.ok) {
			error = result.error ?? 'Delete failed';
			return;
		}
		await load();
	}

	function logout() {
		clearToken();
		goto('/');
	}
</script>

<div class="page">
	<div style="display: flex; align-items: center">
		<h1 style="flex: 1">Your graphs</h1>
		<button class="btn" onclick={logout}>Sign out</button>
	</div>
	{#if error}<p class="error-text">{error}</p>{/if}
	{#if loading}
		<p class="muted">Loading…</p>
	{:else}
		{#each graphs as graph (graph.id)}
			<div class="card row">
				<div class="grow">
					<a href={`/graphs/${graph.slug}`} style="font-weight: 600">{graph.name}</a>
					<div class="muted" style="font-size: 12px">{graph.slug} · {graph.role}</div>
				</div>
				{#if graph.role === 'owner'}
					<a class="btn" style="text-decoration: none" href={`/graphs/${graph.slug}/settings`}>Settings</a>
					<button class="btn" onclick={() => renameGraph(graph)}>Rename</button>
					<button class="btn danger" onclick={() => deleteGraph(graph)}>Delete</button>
				{/if}
			</div>
		{:else}
			<p class="muted">No graphs yet — create your first one below.</p>
		{/each}
		<div class="card">
			<label class="lbl" for="new-graph">New graph</label>
			<div style="display: flex; gap: 8px">
				<input
					id="new-graph"
					class="field"
					bind:value={newName}
					placeholder="Graph name"
					onkeydown={(e) => e.key === 'Enter' && createGraph()}
				/>
				<button class="btn primary" onclick={createGraph}>Create</button>
			</div>
			{#if newName.trim()}<div class="muted" style="font-size: 11px; margin-top: 4px">
					slug: {slugify(newName)}
				</div>{/if}
		</div>
	{/if}
</div>
