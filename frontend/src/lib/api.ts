// HTTP client for the Outcome Engineering API.
//
// Auth resolution order:
// 1. share token (public read-only routes) — sent as X-Share-Token
// 2. token provided by the server layout (oauth2-proxy forwarded access token)
// 3. dev token stored in localStorage (simulation-mode login)
import { PUBLIC_API_BASE_URL } from '$env/static/public';

const TOKEN_KEY = 'oe_token';

export function apiBase(): string {
	return (PUBLIC_API_BASE_URL || 'http://localhost:8000').replace(/\/$/, '');
}

export function storedToken(): string | null {
	if (typeof localStorage === 'undefined') return null;
	return localStorage.getItem(TOKEN_KEY);
}

export function storeToken(token: string): void {
	localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
	localStorage.removeItem(TOKEN_KEY);
}

let proxyToken: string | null = null;
export function setProxyToken(token: string | null): void {
	proxyToken = token;
}

export function activeToken(): string | null {
	return proxyToken || storedToken();
}

export interface ApiResult<T = Record<string, unknown>> {
	ok: boolean;
	status: number;
	data: T;
	error?: string;
}

export async function api<T = Record<string, unknown>>(
	method: string,
	path: string,
	body?: unknown,
	options: { shareToken?: string } = {}
): Promise<ApiResult<T>> {
	const headers: Record<string, string> = { 'Content-Type': 'application/json' };
	if (options.shareToken) {
		headers['X-Share-Token'] = options.shareToken;
	} else {
		const token = activeToken();
		if (token) headers['Authorization'] = `Bearer ${token}`;
	}
	try {
		const response = await fetch(apiBase() + path, {
			method,
			headers,
			body: body === undefined ? undefined : JSON.stringify(body)
		});
		const data = (await response.json().catch(() => ({}))) as T & { detail?: string };
		if (!response.ok) {
			return { ok: false, status: response.status, data, error: data.detail || response.statusText };
		}
		return { ok: true, status: response.status, data };
	} catch (error) {
		return { ok: false, status: 0, data: {} as T, error: String(error) };
	}
}
