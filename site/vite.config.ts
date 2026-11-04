import { svelte } from '@sveltejs/vite-plugin-svelte'
import { defineConfig } from 'vite'

// base relative : le site fonctionne sur GitHub Pages (sous-chemin /<repo>/) comme en local.
export default defineConfig({
  base: './',
  plugins: [svelte()],
})
