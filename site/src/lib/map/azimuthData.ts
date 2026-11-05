/**
 * Assemble les entités des azimuts pour la carte : fiches des supports cochés (detail/<dep>.json, en cache),
 * faisceaux à dessiner, puis recherche des liaisons FH (fiches des supports candidats chargées à la demande).
 */
import type { FeatureCollection } from 'geojson'
import { beams, type AzState } from '../azimuthSelection'
import { beamKey, coneFeatures, fhFeatures, type PlacedBeam, type ResolvedLink } from '../azimuthFeatures'
import { loadSupportDetail } from '../detail'
import { findLink, type LinkContext } from '../fhLinks'
import { depOf, inseeOf, type SupportIndex } from '../supports'
import type { Services } from '../services'

export interface AzimuthLayers { cones: FeatureCollection; fh: FeatureCollection }

/** Résultats des recherches de liaison, par faisceau (support | exploitant | azimut). */
const linkCache = new Map<string, ResolvedLink | null>()

function familleOf(services: Services | null) {
  const m = new Map(services?.syss.map((x) => [x.nom, x.famille]) ?? [])
  // Avant le chargement de la table des services, on reconnaît les FH à leur libellé (FH, FH ABI).
  return (sys: string) => m.get(sys) ?? (/^FH\b/.test(sys) ? 'Faisceau hertzien' : 'Autre')
}

const detailOf = (index: SupportIndex, i: number) => loadSupportDetail(depOf(inseeOf(index, i)), index.id[i])

/**
 * Calcule les couches. `update` est appelé une première fois avec les cônes et des traits FH provisoires
 * (longueur fixe), puis une seconde fois une fois les liaisons trouvées. `stale()` interrompt un calcul dépassé.
 */
export async function buildAzimuth(
  index: SupportIndex, services: Services | null, st: AzState,
  update: (l: AzimuthLayers) => void, stale: () => boolean,
): Promise<void> {
  const famille = familleOf(services)
  const placed: PlacedBeam[] = []
  for (const e of st.list) {
    const i = index.byId.get(e.id)
    if (i === undefined) continue
    const d = await detailOf(index, i)
    if (stale()) return
    if (!d) continue
    for (const b of beams(d, e.rows, famille)) placed.push({ ...b, id: e.id, lat: index.lat[i], lon: index.lon[i] })
  }
  const render = () => update({ cones: coneFeatures(placed, st.len, st.ap), fh: fhFeatures(placed, linkCache, st.len) })
  render()

  const todo = placed.filter((b) => b.fh && !linkCache.has(beamKey(b)))
  if (!todo.length || !services) return // sans la table des services, on ne peut pas juger les candidats

  // Exploitant × FH par support, d'après la table des services.
  const fhSys = new Uint8Array(services.syss.length)
  services.syss.forEach((x, k) => { fhSys[k] = +(x.famille === 'Faisceau hertzien') })
  const grpIdx = new Map(services.grps.map((g, k) => [g.nom, k]))
  const ctx: LinkContext = {
    pts: index,
    hasFh: (i, grp) => {
      const g = grpIdx.get(grp)
      for (let r = services.start[i]; r < services.start[i + 1]; r++) if (services.grp[r] === g && fhSys[services.sys[r]]) return true
      return false
    },
    fhAzimuths: async (i, grp) => {
      const d = await detailOf(index, i)
      return d ? beams(d, null, famille).filter((b) => b.fh && b.grp === grp).map((b) => b.az) : []
    },
  }
  for (const b of todo) {
    const self = index.byId.get(b.id)!
    const l = await findLink(self, b.az, b.grp, ctx)
    if (stale()) return
    linkCache.set(beamKey(b), l && { id: index.id[l.i], lat: index.lat[l.i], lon: index.lon[l.i], dist: l.dist, level: l.level })
  }
  render()
}
