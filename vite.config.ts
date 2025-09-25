import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

import { viteStaticCopy } from 'vite-plugin-static-copy';

// /** @type {import('vite').Plugin} */
// const viteServerConfig = {
// 	name: 'log-request-middleware',
// 	configureServer(server) {
// 		server.middlewares.use((req, res, next) => {
// 			res.setHeader('Access-Control-Allow-Origin', '*');
// 			res.setHeader('Access-Control-Allow-Methods', 'GET');
// 			res.setHeader('Cross-Origin-Opener-Policy', 'same-origin');
// 			res.setHeader('Cross-Origin-Embedder-Policy', 'require-corp');
// 			next();
// 		});
// 	}
// };

// Base path is controlled by SvelteKit (paths.base via PUBLIC_BASE_PATH)

export default defineConfig({
	plugins: [
		sveltekit(),
		viteStaticCopy({
			targets: [
				{
					src: 'node_modules/onnxruntime-web/dist/*.jsep.*',

					dest: 'wasm'
				}
			]
		})
	],
	define: {
		APP_VERSION: JSON.stringify(process.env.npm_package_version),
		APP_BUILD_HASH: JSON.stringify(process.env.APP_BUILD_HASH || 'dev-build')
	},
	// base is set by SvelteKit; avoid overriding to prevent warnings
	build: {
		sourcemap: true
	},
	worker: {
		format: 'es'
	},
	server: {
		port: 5173,
		proxy: {
			[`/kael/api/`]: {
				target: 'http://localhost:8083',
				changeOrigin: true
			},
			[`/kael/ws`]: {
				target: 'http://localhost:8083',
				ws: true,
				changeOrigin: true
			}
		}
	}
});
