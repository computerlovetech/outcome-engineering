<script lang="ts">
	import { page } from '$app/state';
	import GraphView from '$lib/GraphView.svelte';
</script>

<GraphView graphRef={page.params.slug ?? ''} />
