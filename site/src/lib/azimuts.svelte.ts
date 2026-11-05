/**
 * État partagé des azimuts affichés sur la carte (fiche support, carte, panneau Azimuts).
 * Persiste quand on ferme la fiche ; synchronisé avec l'URL par la page Carte.
 */
import { AZ_DEFAULTS, type AzEntry, type AzState } from './azimuthSelection'

export const azimuts = $state<AzState>({ list: [], len: AZ_DEFAULTS.len, ap: AZ_DEFAULTS.ap })

export const entryOf = (id: number): AzEntry | undefined => azimuts.list.find((e) => e.id === id)

/** État de la case globale d'un support : tout, partiel ou rien. */
export function globalState(id: number): 'tout' | 'partiel' | 'rien' {
  const e = entryOf(id)
  return !e ? 'rien' : e.rows === null ? 'tout' : 'partiel'
}

export const rowChecked = (id: number, key: string) => {
  const e = entryOf(id)
  return !!e && (e.rows === null || e.rows.includes(key))
}

/** Case globale : coche tout le support, ou le retire. */
export function setAll(id: number, on: boolean) {
  const rest = azimuts.list.filter((e) => e.id !== id)
  azimuts.list = on ? [...rest, { id, rows: null }] : rest
}

/**
 * Case d'une ligne. `all` = clés de toutes les lignes cochables du support : quand elles sont toutes cochées,
 * on repasse à « tout » ; quand aucune ne l'est, le support est retiré.
 */
export function toggleRow(id: number, key: string, all: string[]) {
  const e = entryOf(id)
  const cur = new Set(e ? (e.rows ?? all) : [])
  if (cur.has(key)) cur.delete(key)
  else cur.add(key)
  const rows = all.filter((k) => cur.has(k))
  const rest = azimuts.list.filter((x) => x.id !== id)
  if (!rows.length) azimuts.list = rest
  else if (rows.length === all.length) azimuts.list = e ? azimuts.list.map((x) => (x.id === id ? { id, rows: null } : x)) : [...rest, { id, rows: null }]
  else azimuts.list = e ? azimuts.list.map((x) => (x.id === id ? { id, rows } : x)) : [...rest, { id, rows }]
}

export const remove = (id: number) => (azimuts.list = azimuts.list.filter((e) => e.id !== id))
export const clearAll = () => (azimuts.list = [])
