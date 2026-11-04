/** Table des services (services.json + services.bin.gz). Voir pipeline/export.py:write_services. */
import { loadJSON } from './data'

export interface SysInfo { nom: string; famille: string; generation: string | null; bande: string | null }
export interface GrpInfo { nom: string; categorie: string }

interface Meta {
  version: number
  n: number
  m: number
  dictionnaires: { grp: GrpInfo[]; sys: SysInfo[]; bandes: [number, number][][] }
}

export interface Services {
  n: number
  m: number
  /** start[i]..start[i+1] : lignes du support i */
  start: Uint32Array
  d: Uint16Array
  bs: Uint16Array
  grp: Uint8Array
  sys: Uint8Array
  grps: GrpInfo[]
  syss: SysInfo[]
  bandes: [number, number][][]
}

let cached: Promise<Services> | null = null

export function loadServices(): Promise<Services> {
  cached ??= Promise.all([loadJSON<Meta>('services.json'), fetchGunzip('services.bin.gz')]).then(([meta, buf]) => {
    const { n, m } = meta
    if (buf.byteLength !== 6 * m + n) throw new Error('services.bin.gz : taille inattendue')
    const d = new Uint16Array(buf, 0, m)
    const bs = new Uint16Array(buf, 2 * m, m)
    const cnt = new Uint8Array(buf, 4 * m, n)
    const grp = new Uint8Array(buf, 4 * m + n, m)
    const sys = new Uint8Array(buf, 5 * m + n, m)
    const start = new Uint32Array(n + 1)
    for (let i = 0; i < n; i++) start[i + 1] = start[i] + cnt[i]
    return { n, m, start, d, bs, grp, sys, grps: meta.dictionnaires.grp, syss: meta.dictionnaires.sys, bandes: meta.dictionnaires.bandes }
  })
  cached.catch(() => (cached = null))
  return cached
}

async function fetchGunzip(name: string): Promise<ArrayBuffer> {
  const r = await fetch(`${import.meta.env.BASE_URL}data/${name}`)
  if (!r.ok || !r.body) throw new Error(`${name} : HTTP ${r.status}`)
  // Certains serveurs décompressent déjà (Content-Encoding) : on vérifie l'en-tête gzip.
  const buf = await r.arrayBuffer()
  const head = new Uint8Array(buf, 0, 2)
  if (head[0] !== 0x1f || head[1] !== 0x8b) return buf
  const stream = new Blob([buf]).stream().pipeThrough(new DecompressionStream('gzip'))
  return new Response(stream).arrayBuffer()
}
