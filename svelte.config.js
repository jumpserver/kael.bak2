import adapter from '@sveltejs/adapter-static';
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';

// Normalize PUBLIC_BASE_PATH to start with '/' and have no trailing '/'
// Default to '/kael' to match Vite's dev base
const rawBase = (process.env.PUBLIC_BASE_PATH || '/kael').trim();
let normalizedBase = rawBase;
if (normalizedBase && !normalizedBase.startsWith('/')) normalizedBase = `/${normalizedBase}`;
if (normalizedBase !== '/' && normalizedBase.endsWith('/'))
	normalizedBase = normalizedBase.slice(0, -1);

/** @type {import('@sveltejs/kit').Config} */
const config = {
	// Consult https://kit.svelte.dev/docs/integrations#preprocessors
	// for more information about preprocessors
	preprocess: vitePreprocess(),
	kit: {
		// adapter-auto only supports some environments, see https://kit.svelte.dev/docs/adapter-auto for a list.
		// If your environment is not supported or you settled on a specific environment, switch out the adapter.
		// See https://kit.svelte.dev/docs/adapters for more information about adapters.
		adapter: adapter({
			pages: 'build',
			assets: 'build',
			fallback: 'index.html'
		}),
		paths: {
			base: normalizedBase || ''
		}
	},
	vitePlugin: {
		// inspector: {
		// 	toggleKeyCombo: 'meta-shift', // Key combination to open the inspector
		// 	holdMode: false, // Enable or disable hold mode
		// 	showToggleButton: 'always', // Show toggle button ('always', 'active', 'never')
		// 	toggleButtonPos: 'bottom-right' // Position of the toggle button
		// }
	},
	onwarn: (warning, handler) => {
		const { code } = warning;
		if (code === 'css-unused-selector') return;

		handler(warning);
	}
};

export default config;
