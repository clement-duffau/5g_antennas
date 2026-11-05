/**
 * Azimuts affichés sur la carte : sélection par support, réglages, encodage dans l'URL et choix des antennes.
 *
 * URL : az=<id>,<id>.<ligne>.<ligne>&azl=<mètres>&azo=<degrés>
 *   - un numéro seul : tous les secteurs directionnels du support ;
 *   - sinon les lignes cochées, notées <n° de station>_<système sans espaces> (ex. 0422750123_5GNR3500).
 * Le numéro de station ANFR est stable d'un mois sur l'autre ; un support, une station ou un système disparu
 * est simplement ignoré. azl et azo sont omis à leur valeur par défaut.
 */
import type { Antenne, Station, SupportDetail } from './detail'

export interface AzEntry { id: number; rows: string[] | null }
export interface AzState { list: AzEntry[]; len: number; ap: number }

export const AZ_DEFAULTS = { len: 1000, ap: 65 } as const
export const AZ_LIMITS = { len: [200, 5000], ap: [10, 120] } as const

export const sysCode = (s: string) => s.replace(/\s+/g, '')
export const rowKey = (sta: string, sys: string) => `${sta}_${sysCode(sys)}`

const clamp = (v: number, [lo, hi]: readonly [number, number]) => Math.min(hi, Math.max(lo, v))
const ROW_RE = /^[0-9A-Za-z]+_[^.,_][^.,]*$/

export function encode(st: AzState): Record<string, string | null> {
  return {
    az: st.list.length ? st.list.map((e) => [e.id, ...(e.rows ?? [])].join('.')).join(',') : null,
    azl: st.list.length && st.len !== AZ_DEFAULTS.len ? String(st.len) : null,
    azo: st.list.length && st.ap !== AZ_DEFAULTS.ap ? String(st.ap) : null,
  }
}

export function decode(p: Record<string, string | undefined>): AzState {
  const list: AzEntry[] = []
  const seen = new Set<number>()
  for (const part of (p.az ?? '').split(',')) {
    const [head, ...rows] = part.split('.')
    const id = Number(head)
    if (!head || !Number.isInteger(id) || id <= 0 || seen.has(id)) continue
    seen.add(id)
    const ok = rows.filter((r) => ROW_RE.test(r))
    list.push({ id, rows: ok.length ? [...new Set(ok)] : null })
  }
  const len = Number(p.azl), ap = Number(p.azo)
  return {
    list,
    len: Number.isFinite(len) && p.azl ? clamp(Math.round(len), AZ_LIMITS.len) : AZ_DEFAULTS.len,
    ap: Number.isFinite(ap) && p.azo ? clamp(Math.round(ap), AZ_LIMITS.ap) : AZ_DEFAULTS.ap,
  }
}

// ------------------------------------------------------------------ lignes et antennes d'un support

export const isDirectional = (a: Antenne | undefined): a is Antenne & { az: number } => !!a && a.r === 'D' && a.az != null

export interface Row { key: string; sta: string; grp: string; sys: string; antennas: number[] }

/** Lignes station × système d'un support, avec leurs antennes directionnelles (dans l'ordre d'affichage). */
export function rowsOf(d: SupportDetail): Row[] {
  const out = new Map<string, Row>()
  for (const st of d.st) {
    for (const e of st.emr) {
      const key = rowKey(st.sta, e.s)
      const row = out.get(key) ?? { key, sta: st.sta, grp: st.grp, sys: e.s, antennas: [] }
      for (const a of e.a) if (isDirectional(st.ant.find((x) => x.id === a)) && !row.antennas.includes(a)) row.antennas.push(a)
      out.set(key, row)
    }
  }
  return [...out.values()]
}

/** Lignes qui ont au moins une antenne directionnelle avec azimut (les seules cochables). */
export const drawableRows = (d: SupportDetail) => rowsOf(d).filter((r) => r.antennas.length > 0)

export interface Beam { grp: string; az: number; fh: boolean }

/**
 * Antennes à dessiner pour une sélection (null = tout le support), dédoublonnées par exploitant et azimut
 * arrondi au degré, comme le diagramme de la fiche. `fh` : antenne utilisée par un système de la famille
 * « Faisceau hertzien ».
 */
export function beams(d: SupportDetail, rows: string[] | null, famille: (sys: string) => string): Beam[] {
  const wanted = rows ? new Set(rows) : null
  const out = new Map<string, Beam>()
  const add = (st: Station, a: Antenne & { az: number }, fh: boolean) => {
    const k = `${st.grp}|${Math.round(a.az) % 360}|${fh ? 'fh' : 'c'}`
    if (!out.has(k)) out.set(k, { grp: st.grp, az: a.az, fh })
  }
  for (const st of d.st) {
    const used = new Set<number>()
    for (const e of st.emr) {
      const selected = !wanted || wanted.has(rowKey(st.sta, e.s))
      for (const id of e.a) {
        used.add(id)
        const a = st.ant.find((x) => x.id === id)
        if (selected && isDirectional(a)) add(st, a, famille(e.s) === 'Faisceau hertzien')
      }
    }
    // « Tout » couvre aussi les antennes directionnelles déclarées sans émetteur rattaché.
    if (!wanted) for (const a of st.ant) if (!used.has(a.id) && isDirectional(a)) add(st, a, false)
  }
  return [...out.values()]
}
