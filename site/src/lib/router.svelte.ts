import { untrack } from 'svelte'

/**
 * Routeur minimal par hash, compatible GitHub Pages :
 *   #/carte?s=123&z=12&c=48.11,-1.68   #/statistiques#spectre
 */
export const ROUTES = [
  { path: 'carte', label: 'Carte' },
  { path: 'statistiques', label: 'Statistiques' },
  { path: 'a-propos', label: 'À propos' },
] as const

export type RoutePath = (typeof ROUTES)[number]['path']
const DEFAULT: RoutePath = 'carte'

interface Route { path: RoutePath; anchor: string; params: Record<string, string> }

function parse(): Route {
  const raw = location.hash.replace(/^#\/?/, '')
  const [beforeAnchor, anchor = ''] = raw.split('#')
  const [p, query = ''] = beforeAnchor.split('?')
  const path = (ROUTES.find((r) => r.path === p)?.path ?? DEFAULT) as RoutePath
  return { path, anchor, params: Object.fromEntries(new URLSearchParams(query)) }
}

export const route = $state(parse())

addEventListener('hashchange', () => {
  const next = parse()
  const pageChanged = next.path !== route.path
  route.path = next.path
  route.anchor = next.anchor
  route.params = next.params
  if (pageChanged) scrollTo({ top: 0 })
})

/** Met à jour les paramètres de la page courante sans créer d'entrée d'historique ni recharger. */
export function setParams(params: Record<string, string | number | null | undefined>) {
  // untrack : appelée depuis des effets, la fonction ne doit pas s'abonner à route.params.
  const merged: Record<string, string> = { ...untrack(() => route.params) }
  for (const [k, v] of Object.entries(params)) {
    if (v == null || v === '') delete merged[k]
    else merged[k] = String(v)
  }
  const q = new URLSearchParams(merged).toString().replaceAll('%2C', ',')
  history.replaceState(null, '', `#/${untrack(() => route.path)}${q ? `?${q}` : ''}`)
  route.params = merged
}
