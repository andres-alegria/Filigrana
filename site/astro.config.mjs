import { defineConfig } from 'astro/config';
import { fileURLToPath } from 'node:url';

// The content collection reads from ../content (outside this project's
// root), so Vite needs explicit permission to watch/serve it — otherwise
// editing an article .md during `astro dev` won't trigger a reload.
const repoRoot = fileURLToPath(new URL('..', import.meta.url));

export default defineConfig({
  site: 'https://www.filigrana.hn',
  output: 'static',
  vite: {
    server: {
      fs: { allow: [repoRoot] },
      watch: { ignored: ['!' + repoRoot + 'content/**'] },
    },
  },
});
