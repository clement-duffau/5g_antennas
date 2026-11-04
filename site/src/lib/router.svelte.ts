/** Routeur minimal par hash (#/statistiques) : compatible GitHub Pages sans configuration. */
export const ROUTES = [
  { path: 'statistiques', label: 'Statistiques' },
  { path: 'a-propos', label: 'À propos' },
] as const

export type RoutePath = (typeof ROUTES)[number]['path']
const DEFAULT: RoutePath = 'statistiques'

function parse(): { path: RoutePath; anchor: string } {
  const [p, anchor = ''] = location.hash.replace(/^#\/?/, '').split('#')
  const path = (ROUTES.find((r) => r.path === p)?.path ?? DEFAULT) as RoutePath
  return { path, anchor }
}

export const route = $state(parse())

addEventListener('hashchange', () => {
  const next = parse()
  const pageChanged = next.path !== route.path
  route.path = next.path
  route.anchor = next.anchor
  if (pageChanged) scrollTo({ top: 0 })
})
