<script lang="ts">
	import '../app.css';
	import { setProxyToken } from '$lib/api';

	let { data, children } = $props();
	$effect(() => setProxyToken(data?.proxyToken ?? null));
</script>

{@render children()}
