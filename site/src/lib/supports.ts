/** Index des supports (supports.json) décodé en tableaux typés. Voir pipeline/export.py:write_index. */
import { loadJSON } from './data'

interface RawIndex {
  version: number
  n: number
  deltas: string[]
  echelles: { lat: number; lon: number; h: number; mois_origine: string }
  dictionnaires: { nat: string[]; tpo: string[]; com: [string, string][]; ops: string[]; gen: string[]; fam: string[] }
  colonnes: Record<string, (number | null)[]>
}

export interface SupportIndex {
  n: number
  id: Int32Array
  lat: Float64Array
  lon: Float64Array
  /** hauteur en mètres, NaN si inconnue */
  h: Float32Array
  nat: Int16Array
  tpo: Int16Array
  com: Int32Array
  /** bits 0-3 : Orange, Bouygues, SFR, Free (émetteurs mobiles) ; bit 4 : autres exploitants */
  ops: Uint8Array
  /** bits 0-3 : 2G, 3G, 4G, 5G (tous opérateurs) */
  gen: Uint8Array
  /** un bit par famille de systèmes (dict.fam) */
  fam: Uint32Array
  emr: Int32Array
  exp: Uint8Array
  /** mois de la première / dernière mise en service (0 = inconnu, 1 = janvier 1980) */
  d0: Uint16Array
  d1: Uint16Array
  dict: RawIndex['dictionnaires']
  byId: Map<number, number>
}

let cached: Promise<SupportIndex> | null = null

export function loadSupports(): Promise<SupportIndex> {
  cached ??= loadJSON<RawIndex>('supports.json').then(decode)
  return cached
}

function decode(raw: RawIndex): SupportIndex {
  const c = raw.colonnes
  const n = raw.n
  for (const k of raw.deltas) {
    const v = c[k] as number[]
    for (let i = 1; i < v.length; i++) v[i] += v[i - 1]
  }
  const fill = <T extends { [i: number]: number }>(arr: T, src: (number | null)[], f = (x: number) => x) => {
    for (let i = 0; i < n; i++) arr[i] = f((src[i] ?? 0) as number)
    return arr
  }
  const h = new Float32Array(n)
  for (let i = 0; i < n; i++) h[i] = c.h[i] == null ? NaN : (c.h[i] as number) * raw.echelles.h
  const idx: SupportIndex = {
    n,
    id: fill(new Int32Array(n), c.id),
    lat: fill(new Float64Array(n), c.lat, (x) => x * raw.echelles.lat),
    lon: fill(new Float64Array(n), c.lon, (x) => x * raw.echelles.lon),
    h,
    nat: fill(new Int16Array(n), c.nat),
    tpo: fill(new Int16Array(n), c.tpo),
    com: fill(new Int32Array(n), c.com),
    ops: fill(new Uint8Array(n), c.ops),
    gen: fill(new Uint8Array(n), c.gen),
    fam: fill(new Uint32Array(n), c.fam),
    emr: fill(new Int32Array(n), c.emr),
    exp: fill(new Uint8Array(n), c.exp),
    d0: fill(new Uint16Array(n), c.d0),
    d1: fill(new Uint16Array(n), c.d1),
    dict: raw.dictionnaires,
    byId: new Map(),
  }
  for (let i = 0; i < n; i++) idx.byId.set(idx.id[i], i)
  return idx
}

export const inseeOf = (s: SupportIndex, i: number) => s.dict.com[s.com[i]][0]
export const communeOf = (s: SupportIndex, i: number) => s.dict.com[s.com[i]][1]
/** Code du département (fichier de détail) à partir du code INSEE. */
export const depOf = (insee: string) => insee.slice(0, 2)

export const famBit = (s: SupportIndex, famille: string) => {
  const i = s.dict.fam.indexOf(famille)
  return i < 0 ? 0 : 1 << i
}

/** Mois codé -> "AAAA-MM". */
export const monthLabel = (m: number) =>
  m ? `${1980 + Math.floor((m - 1) / 12)}-${String(((m - 1) % 12) + 1).padStart(2, '0')}` : ''

export const popcount = (x: number) => {
  let c = 0
  while (x) { c += x & 1; x >>= 1 }
  return c
}
