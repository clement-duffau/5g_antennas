/**
 * Filtres combinables de la carte.
 *
 * Deux niveaux :
 *  - critères du support (territoire, nature, hauteur) : testés sur l'index ;
 *  - critères de service (exploitant, technologie, système, bande, date) : un support est retenu si
 *    AU MOINS UNE de ses lignes de service les satisfait TOUS à la fois. « Free + 5G » ne retient donc
 *    pas un support où Free n'a que de la 4G et Orange de la 5G.
 * Au sein d'un même critère, les valeurs sont combinées par OU ; entre critères, par ET.
 */
import type { SupportIndex } from './supports'
import type { Services } from './services'
import { distance } from './geo'

/** Zone « autour de moi » : centre, rayon en mètres et libellé affiché. */
export interface Zone { lat: number; lon: number; r: number; label: string }

export interface Filters {
  ops: string[]      // exploitants (groupes)
  gens: string[]     // 2G, 3G, 4G, 5G
  fams: string[]     // familles de systèmes
  sys: string[]      // systèmes ANFR
  f: [number, number] | null   // bande de fréquence (MHz), chevauchement
  y: [number, number] | null   // années de 1re mise en service du service (exploitant × système) sur le support
  deps: string[]
  com: string | null // code INSEE
  nat: string[]
  h: [number, number] | null   // hauteur (m)
  zone: Zone | null
}

export const EMPTY: Filters = { ops: [], gens: [], fams: [], sys: [], f: null, y: null, deps: [], com: null, nat: [], h: null, zone: null }

export const needsServices = (f: Filters) =>
  f.ops.length > 0 || f.gens.length > 0 || f.fams.length > 0 || f.sys.length > 0 || f.f !== null || f.y !== null

export const isEmpty = (f: Filters) =>
  !needsServices(f) && !f.deps.length && !f.com && !f.nat.length && !f.h && !f.zone

// ------------------------------------------------------------------ URL
const list = (s?: string) => (s ? s.split('|').filter(Boolean) : [])
const pair = (s?: string): [number, number] | null => {
  if (!s) return null
  const [a, b] = s.split('-').map(Number)
  return Number.isFinite(a) && Number.isFinite(b) ? [a, b] : null
}

function zoneFrom(p: Record<string, string>): Zone | null {
  const [lat, lon, r] = (p.zone ?? '').split(',').map(Number)
  if (![lat, lon, r].every(Number.isFinite) || r <= 0) return null
  return { lat, lon, r, label: p.zl || `${lat.toFixed(4)}, ${lon.toFixed(4)}` }
}

export function fromParams(p: Record<string, string>): Filters {
  return {
    zone: zoneFrom(p),
    ops: list(p.op), gens: list(p.gen), fams: list(p.fam), sys: list(p.sys),
    f: pair(p.f), y: pair(p.y), deps: list(p.dep), com: p.com || null, nat: list(p.nat), h: pair(p.h),
  }
}

export function toParams(f: Filters): Record<string, string | null> {
  const j = (a: string[]) => (a.length ? a.join('|') : null)
  const r = (x: [number, number] | null) => (x ? `${x[0]}-${x[1]}` : null)
  return {
    op: j(f.ops), gen: j(f.gens), fam: j(f.fams), sys: j(f.sys), f: r(f.f), y: r(f.y),
    dep: j(f.deps), com: f.com, nat: j(f.nat), h: r(f.h),
    zone: f.zone ? `${f.zone.lat.toFixed(5)},${f.zone.lon.toFixed(5)},${f.zone.r}` : null,
    zl: f.zone ? f.zone.label : null,
  }
}

// ------------------------------------------------------------------ calcul
export interface Result { mask: Uint8Array; count: number }

export function apply(idx: SupportIndex, sv: Services | null, f: Filters): Result {
  const n = idx.n
  const mask = new Uint8Array(n)

  // Critères du support
  const deps = new Set(f.deps)
  const natOk = f.nat.length ? new Uint8Array(idx.dict.nat.length + 1) : null
  if (natOk) f.nat.forEach((x) => { const k = idx.dict.nat.indexOf(x); if (k >= 0) natOk[k] = 1 })
  const comOk = new Uint8Array(idx.dict.com.length)
  const useCom = deps.size > 0 || f.com !== null
  if (useCom) {
    idx.dict.com.forEach(([insee], k) => {
      if (f.com !== null ? insee === f.com : deps.has(insee.slice(0, 2))) comOk[k] = 1
    })
  }

  // Critères de service, précalculés par dictionnaire
  const svc = needsServices(f) && sv
  let grpOk: Uint8Array | null = null, sysOk: Uint8Array | null = null, bsOk: Uint8Array | null = null
  let m0 = 0, m1 = 0
  if (svc) {
    if (f.ops.length) {
      const s = new Set(f.ops)
      grpOk = Uint8Array.from(sv.grps, (g) => +s.has(g.nom))
    }
    if (f.sys.length || f.gens.length || f.fams.length) {
      const ss = new Set(f.sys), gs = new Set(f.gens), fs = new Set(f.fams)
      sysOk = Uint8Array.from(sv.syss, (x) =>
        +((!ss.size || ss.has(x.nom)) && (!gs.size || (x.generation != null && gs.has(x.generation))) && (!fs.size || fs.has(x.famille))))
    }
    if (f.f) {
      const [a, b] = f.f
      bsOk = Uint8Array.from(sv.bandes, (bands) => +bands.some(([lo, hi]) => hi >= a && lo <= b))
    }
    if (f.y) {
      m0 = (f.y[0] - 1980) * 12 + 1
      m1 = (f.y[1] - 1980) * 12 + 12
    }
  }

  // Zone : préfiltre rapide par boîte englobante, puis distance exacte.
  const z = f.zone
  const dLat = z ? z.r / 111320 : 0
  const dLon = z ? z.r / (111320 * Math.cos((z.lat * Math.PI) / 180)) : 0

  let count = 0
  for (let i = 0; i < n; i++) {
    if (z) {
      const la = idx.lat[i], lo = idx.lon[i]
      if (Math.abs(la - z.lat) > dLat || Math.abs(lo - z.lon) > dLon) continue
      if (distance(z.lat, z.lon, la, lo) > z.r) continue
    }
    if (useCom && !comOk[idx.com[i]]) continue
    if (natOk && !natOk[idx.nat[i]]) continue
    if (f.h) {
      const h = idx.h[i]
      if (Number.isNaN(h) || h < f.h[0] || h > f.h[1]) continue
    }
    if (svc) {
      let ok = false
      for (let r = sv.start[i], e = sv.start[i + 1]; r < e; r++) {
        if (grpOk && !grpOk[sv.grp[r]]) continue
        if (sysOk && !sysOk[sv.sys[r]]) continue
        if (bsOk && !bsOk[sv.bs[r]]) continue
        if (f.y) { const d = sv.d[r]; if (d === 0 || d < m0 || d > m1) continue }
        ok = true
        break
      }
      if (!ok) continue
    }
    mask[i] = 1
    count++
  }
  return { mask, count }
}

// ------------------------------------------------------------------ préréglages de bandes
export const BAND_PRESETS: { label: string; f: [number, number]; groupe: string }[] = [
  { label: '700', f: [703, 788], groupe: 'Mobile' },
  { label: '800', f: [791, 862], groupe: 'Mobile' },
  { label: '900', f: [880, 960], groupe: 'Mobile' },
  { label: '1800', f: [1710, 1880], groupe: 'Mobile' },
  { label: '2100', f: [1920, 2170], groupe: 'Mobile' },
  { label: '2600', f: [2500, 2690], groupe: 'Mobile' },
  { label: '3500', f: [3400, 3800], groupe: 'Mobile' },
  { label: 'FM', f: [87.5, 108], groupe: 'Diffusion' },
  { label: 'DAB+', f: [174, 240], groupe: 'Diffusion' },
  { label: 'TNT', f: [470, 694], groupe: 'Diffusion' },
  { label: 'VHF', f: [30, 300], groupe: 'Bandes' },
  { label: 'UHF', f: [300, 3000], groupe: 'Bandes' },
  { label: 'SHF', f: [3000, 30000], groupe: 'Bandes' },
  { label: 'EHF', f: [30000, 300000], groupe: 'Bandes' },
]
