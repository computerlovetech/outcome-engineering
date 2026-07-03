// Minimal, safe markdown -> html (escapes first, then formats a known subset).
// Ported from the old graph.html renderer.

function esc(s: string): string {
	return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

function inline(s: string): string {
	return s
		.replace(/`([^`]+)`/g, '<code>$1</code>')
		.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
}

export function renderMarkdown(src: string): string {
	const lines = src.split('\n');
	let html = '';
	let inUl = false;
	let inCode = false;
	let code = '';
	const closeUl = () => {
		if (inUl) {
			html += '</ul>';
			inUl = false;
		}
	};
	for (const line of lines) {
		if (line.trim().startsWith('```')) {
			if (inCode) {
				html += '<pre><code>' + esc(code) + '</code></pre>';
				code = '';
				inCode = false;
			} else {
				closeUl();
				inCode = true;
			}
			continue;
		}
		if (inCode) {
			code += line + '\n';
			continue;
		}
		if (/^###\s+/.test(line)) {
			closeUl();
			html += '<h3>' + inline(esc(line.replace(/^###\s+/, ''))) + '</h3>';
			continue;
		}
		if (/^##\s+/.test(line)) {
			closeUl();
			html += '<h2>' + inline(esc(line.replace(/^##\s+/, ''))) + '</h2>';
			continue;
		}
		if (/^#\s+/.test(line)) {
			closeUl();
			html += '<h3>' + inline(esc(line.replace(/^#\s+/, ''))) + '</h3>';
			continue;
		}
		if (/^\s*[-*]\s+/.test(line)) {
			if (!inUl) {
				html += '<ul>';
				inUl = true;
			}
			html += '<li>' + inline(esc(line.replace(/^\s*[-*]\s+/, ''))) + '</li>';
			continue;
		}
		if (line.trim() === '') {
			closeUl();
			continue;
		}
		closeUl();
		html += '<p>' + inline(esc(line)) + '</p>';
	}
	if (inCode) html += '<pre><code>' + esc(code) + '</code></pre>';
	closeUl();
	return html;
}

// Drop the leading "# Title" from a node body for panel display.
export function stripFrontHeading(body: string): string {
	return body.replace(/^#\s+.*\n/, '').trim();
}

export function slugify(t: string): string {
	return t
		.toLowerCase()
		.trim()
		.replace(/[^a-z0-9]+/g, '-')
		.replace(/^-+|-+$/g, '');
}
