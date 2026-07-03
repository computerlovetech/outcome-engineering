import type { LayoutServerLoad } from './$types';

// When oauth2-proxy fronts the app (auth profile), it forwards the user's
// OIDC access token in this header; the client then uses it as the API bearer.
export const load: LayoutServerLoad = ({ request }) => {
	return {
		proxyToken: request.headers.get('x-forwarded-access-token')
	};
};
