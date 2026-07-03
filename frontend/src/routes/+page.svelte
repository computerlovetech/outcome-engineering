<script lang="ts">
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';
	import { api, activeToken, storeToken } from '$lib/api';

	let token = $state('');
	let error = $state('');
	let checking = $state(true);

	onMount(async () => {
		if (activeToken()) {
			const me = await api('GET', '/api/me');
			if (me.ok) {
				goto('/graphs');
				return;
			}
		}
		checking = false;
	});

	async function login() {
		error = '';
		if (!token.trim()) {
			error = 'Enter a token.';
			return;
		}
		storeToken(token.trim());
		const me = await api('GET', '/api/me');
		if (!me.ok) {
			error = `Login failed: ${me.error}`;
			return;
		}
		goto('/graphs');
	}
</script>

<div class="page">
	<h1>Outcome Engineering</h1>
	<p class="muted">
		Product graphs that humans and agents can trace and update: vision, strategy, ICPs, outcomes,
		opportunities, solutions, and the flywheel that connects them.
	</p>
	{#if checking}
		<p class="muted">Checking session…</p>
	{:else}
		<div class="card">
			<h3 style="margin-top: 0">Sign in</h3>
			<p class="muted">
				In production this app sits behind your OIDC provider (oauth2-proxy) and you are signed in
				automatically. Against a dev server running in simulation mode, enter any token — it
				becomes your dev identity.
			</p>
			<label class="lbl" for="token">Dev token</label>
			<input id="token" class="field" bind:value={token} placeholder="dev" onkeydown={(e) => e.key === 'Enter' && login()} />
			{#if error}<p class="error-text">{error}</p>{/if}
			<div class="actions">
				<button class="btn primary" onclick={login}>Sign in</button>
			</div>
		</div>
	{/if}
</div>
