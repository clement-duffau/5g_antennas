/** Fiches détaillées des supports, découpées par département (detail/<dep>.json). */
import { loadJSON } from './data'

export interface Emetteur { s: string; d: string | null; b: [number, number][]; a: number[]; n: number }
export interface Antenne { id: number; t: string | null; dim: number | null; r: string | null; az: number | null; h: number | null }
export interface Station {
  sta: string; exp: string; grp: string
  impl: string | null; serv: string | null; mod: string | null
  emr: Emetteur[]; ant: Antenne[]
}
export interface SupportDetail {
  lat: number; lon: number; h: number | null; nat: string | null; tpo: string | null
  adr: string | null; cp: string | null; insee: string; com: string
  st: Station[]
}

export const loadDepartement = (dep: string) => loadJSON<Record<string, SupportDetail>>(`detail/${dep}.json`)

export async function loadSupportDetail(dep: string, id: number): Promise<SupportDetail | undefined> {
  return (await loadDepartement(dep))[String(id)]
}
