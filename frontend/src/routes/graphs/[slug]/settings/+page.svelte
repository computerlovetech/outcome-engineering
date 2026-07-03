<script lang="ts">
	import { page } from '$app/state';
	import { onMount } from 'svelte';
	import { api } from '$lib/api';

	const slug = page.params.slug;

	interface Member {
		userId: string;
		email: string | null;
		name: string | null;
		role: string;
	}
	interface ShareLink {
		id: string;
		token: string;
		createdAt: string;
		revokedAt: string | null;
	}

	let members = $state<Member[]>([]);
	let shareLinks = $state<ShareLink[]>([]);
	let error = $state('');
	let notice = $state('');
	let newEmail = $state('');
	let newRole = $state('viewer');

	onMount(load);

	async function load() {
		const [membersResult, linksResult] = await Promise.all([
			api<{ members: Member[] }>('GET', `/api/graphs/${slug}/members`),
			api<{ shareLinks: ShareLink[] }>('GET', `/api/graphs/${slug}/share-links`)
		]);
		if (membersResult.ok) members = membersResult.data.members;
		else error = membersResult.error ?? 'Failed to load members';
		if (linksResult.ok) shareLinks = linksResult.data.shareLinks;
	}

	async function addMember() {
		error = '';
		if (!newEmail.trim()) return;
		const result = await api('PUT', `/api/graphs/${slug}/members/${encodeURIComponent(newEmail.trim())}`, {
			role: newRole
		});
		if (!result.ok) {
			error = result.error ?? 'Failed to add member';
			return;
		}
		newEmail = '';
		await load();
	}

	async function setRole(member: Member, role: string) {
		const result = await api('PUT', `/api/graphs/${slug}/members/${member.userId}`, { role });
		if (!result.ok) error = result.error ?? 'Failed to change role';
		await load();
	}

	async function removeMember(member: Member) {
		if (!confirm(`Remove ${member.email ?? member.userId} from this graph?`)) return;
		const result = await api('DELETE', `/api/graphs/${slug}/members/${member.userId}`);
		if (!result.ok) error = result.error ?? 'Failed to remove member';
		await load();
	}

	async function createShareLink() {
		const result = await api('POST', `/api/graphs/${slug}/share-links`);
		if (!result.ok) error = result.error ?? 'Failed to create share link';
		await load();
	}

	async function revokeShareLink(link: ShareLink) {
		if (!confirm('Revoke this share link? Anyone using it loses access.')) return;
		const result = await api('DELETE', `/api/graphs/${slug}/share-links/${link.id}`);
		if (!result.ok) error = result.error ?? 'Failed to revoke link';
		await load();
	}

	function shareUrl(link: ShareLink): string {
		return `${location.origin}/share/${link.token}`;
	}

	async function copyLink(link: ShareLink) {
		await navigator.clipboard.writeText(shareUrl(link));
		notice = 'Link copied.';
		setTimeout(() => (notice = ''), 2000);
	}
</script>

<div class="page">
	<p><a href={`/graphs/${slug}`}>← back to graph</a></p>
	<h1>Settings · {slug}</h1>
	{#if error}<p class="error-text">{error}</p>{/if}
	{#if notice}<p class="muted">{notice}</p>{/if}

	<div class="card">
		<h3 style="margin-top: 0">Members</h3>
		<table class="plain">
			<tbody>
				{#each members as member (member.userId)}
					<tr>
						<td>{member.name ?? member.email ?? member.userId}</td>
						<td class="muted">{member.email ?? ''}</td>
						<td>
							<select
								class="field"
								value={member.role}
								onchange={(e) => setRole(member, (e.target as HTMLSelectElement).value)}
							>
								<option value="owner">owner</option>
								<option value="editor">editor</option>
								<option value="viewer">viewer</option>
							</select>
						</td>
						<td><button class="btn danger" onclick={() => removeMember(member)}>Remove</button></td>
					</tr>
				{/each}
			</tbody>
		</table>
		<label class="lbl" for="member-email">Add member (they must have logged in once)</label>
		<div style="display: flex; gap: 8px">
			<input id="member-email" class="field" bind:value={newEmail} placeholder="email@example.com" />
			<select class="field" style="width: 120px" bind:value={newRole}>
				<option value="viewer">viewer</option>
				<option value="editor">editor</option>
				<option value="owner">owner</option>
			</select>
			<button class="btn primary" onclick={addMember}>Add</button>
		</div>
	</div>

	<div class="card">
		<h3 style="margin-top: 0">Public share links</h3>
		<p class="muted">
			Anyone with a link can view this graph read-only, without logging in.
		</p>
		{#each shareLinks.filter((l) => !l.revokedAt) as link (link.id)}
			<div class="card row" style="margin: 8px 0">
				<code class="grow" style="font-size: 11px; overflow-wrap: anywhere">{shareUrl(link)}</code>
				<button class="btn" onclick={() => copyLink(link)}>Copy</button>
				<button class="btn danger" onclick={() => revokeShareLink(link)}>Revoke</button>
			</div>
		{:else}
			<p class="muted">No active share links.</p>
		{/each}
		<button class="btn primary" onclick={createShareLink}>Create share link</button>
	</div>
</div>
