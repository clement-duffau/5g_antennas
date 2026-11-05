<script lang="ts">
  import { ROUTES, route } from './lib/router.svelte'
  import { theme, applyTheme } from './lib/theme.svelte'
  import Stats from './pages/Stats.svelte'
  import About from './pages/About.svelte'
  // La carte (MapLibre, ~1 Mo) n'est chargée que si l'on ouvre la page Carte.
  const loadMap = () => import('./pages/MapPage.svelte')
  const loadFrise = () => import('./pages/Frise.svelte')

  $effect(() => { applyTheme() })

  // Défilement vers l'ancre interne (#/statistiques#spectre) une fois la page rendue.
  $effect(() => {
    const a = route.anchor
    if (!a) return
    const tryScroll = (n = 0) => {
      const el = document.getElementById(a)
      if (el) el.scrollIntoView({ block: 'start' })
      else if (n < 40) setTimeout(() => tryScroll(n + 1), 50)
    }
    tryScroll()
  })
</script>

<a class="skip" href="#contenu">Aller au contenu</a>
<header class="top">
  <div class="inner">
    <a class="brand" href="#/" aria-label="Atlas des antennes radio, accueil">
      <svg viewBox="0 0 32 32" width="26" height="26" aria-hidden="true">
        <path d="M16 9v17M11 26l5-17 5 17M8 9a11 11 0 0 1 16 0M11 12a6.5 6.5 0 0 1 10 0" fill="none"
          stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
      </svg>
      <span>Atlas des antennes radio</span>
    </a>
    <nav aria-label="Pages">
      {#each ROUTES as r (r.path)}
        <a href="#/{r.path}" aria-current={route.path === r.path ? 'page' : undefined}>{r.label}</a>
      {/each}
    </nav>
    <button class="theme" type="button" onclick={() => (theme.value = theme.value === 'dark' ? 'light' : 'dark')}
      aria-label={theme.value === 'dark' ? 'Passer au thème clair' : 'Passer au thème sombre'}>
      {#if theme.value === 'dark'}
        <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true"><circle cx="12" cy="12" r="4.5" fill="none" stroke="currentColor" stroke-width="1.8"/><path d="M12 2v2.5M12 19.5V22M2 12h2.5M19.5 12H22M4.9 4.9l1.8 1.8M17.3 17.3l1.8 1.8M4.9 19.1l1.8-1.8M17.3 6.7l1.8-1.8" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg>
      {:else}
        <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true"><path d="M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5Z" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"/></svg>
      {/if}
    </button>
  </div>
</header>

<main id="contenu" class:full={route.path === 'carte'}>
  {#if route.path === 'a-propos'}
    <About />
  {:else if route.path === 'statistiques'}
    <Stats />
  {:else if route.path === 'frise'}
    {#await loadFrise() then F}<F.default />{/await}
  {:else}
    {#await loadMap() then M}<M.default />{/await}
  {/if}
</main>

{#if route.path !== 'carte'}
<footer>
  <div class="foot"><p>
    Données : <a href="https://www.data.gouv.fr/fr/datasets/donnees-sur-les-installations-radioelectriques-de-plus-de-5-watts-1/">ANFR, installations radioélectriques de plus de 5 W</a>
    (Licence Ouverte 2.0). Hors Aviation civile, Défense et Intérieur.
    <a href="#/a-propos">Méthodologie</a>.
  </p></div>
</footer>
{/if}

<style>
  .skip { position: absolute; left: -999px; top: 8px; background: var(--accent); color: var(--accent-ink); padding: 8px 12px; z-index: 50; border-radius: var(--radius); }
  .skip:focus { left: 8px; }
  .top {
    position: sticky; top: 0; z-index: 20;
    background: color-mix(in srgb, var(--page) 88%, transparent);
    backdrop-filter: blur(8px);
    border-bottom: 1px solid var(--line);
  }
  .inner, main, footer { max-width: var(--maxw); margin-inline: auto; padding-inline: var(--gutter); }
  main.full { max-width: none; padding: 0; }
  .top .inner { max-width: none; }
  .inner { display: flex; align-items: center; gap: 24px; height: 56px; }
  .brand { display: flex; align-items: center; gap: 10px; color: var(--text); text-decoration: none; font-weight: 640; font-stretch: 115%; white-space: nowrap; }
  .brand svg { color: var(--accent); }
  nav { display: flex; gap: 4px; margin-left: auto; overflow-x: auto; }
  nav a { color: var(--text-2); text-decoration: none; padding: 6px 10px; border-radius: var(--radius); font-size: 0.92rem; white-space: nowrap; }
  nav a:hover { color: var(--text); background: var(--surface-2); }
  nav a[aria-current='page'] { color: var(--text); box-shadow: inset 0 -2px 0 var(--accent); border-radius: 0; }
  .theme { background: none; border: 1px solid var(--line-strong); border-radius: var(--radius); width: 34px; height: 34px; display: grid; place-items: center; color: var(--text-2); cursor: pointer; flex: none; }
  .theme:hover { color: var(--text); }
  footer { color: var(--muted); font-size: 0.85rem; }
  .foot { border-top: 1px solid var(--line); padding-block: 28px 40px; }
  @media (max-width: 640px) {
    .inner { gap: 10px; }
    .brand span { display: none; }
  }
</style>
