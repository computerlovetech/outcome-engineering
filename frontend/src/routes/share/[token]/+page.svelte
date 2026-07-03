<script lang="ts">
	import { page } from '$app/state';
	import { onMount } from 'svelte';
	import { api } from '$lib/api';
	import GraphView from '$lib/GraphView.svelte';

	const token = page.params.token;
	let graphRef = $state('');
	let error = $state('');

	onMount(async () => {
		const result = await api<{ graph: { slug: string } }>('GET', `/api/share/${token}`, undefined, {
			shareToken: token
		});
		if (!result.ok) {
			error = result.error ?? 'This share link is invalid or has been revoked.';
			return;
		}
		graphRef = result.data.graph.slug;
	});
</script>

{#if error}
	<div class="page">
		<h1>Link unavailable</h1>
		<p class="error-text">{error}</p>
	</div>
{:else if graphRef}
	<GraphView {graphRef} shareToken={token} />
{:else}
	<div class="page"><p class="muted">Loading…</p></div>
{/if}
