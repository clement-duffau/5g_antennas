import { describe, expect, it } from 'vitest'
import { beamKey, coneFeatures, fhFeatures, opIndex, type PlacedBeam } from './azimuthFeatures'
import { distance } from './geo'

const B: PlacedBeam[] = [
  { id: 1, lat: 48.1, lon: -1.6, grp: 'Free', az: 120, fh: false },
  { id: 1, lat: 48.1, lon: -1.6, grp: 'TDF', az: 10, fh: false },
  { id: 1, lat: 48.1, lon: -1.6, grp: 'Orange', az: 77.6, fh: true },
  { id: 2, lat: 48.2, lon: -1.5, grp: 'Orange', az: 200, fh: true },
]

describe('cônes', () => {
  it('un polygone par faisceau non FH, partant du support', () => {
    const fc = coneFeatures(B, 1000, 65)
    expect(fc.features).toHaveLength(2)
    const ring = fc.features[0].geometry.coordinates[0]
    expect(ring[0]).toEqual([-1.6, 48.1])
    expect(ring).toHaveLength(27)
    expect(fc.features.map((f) => f.properties!.op)).toEqual([3, 4])
    expect(opIndex('Bouygues Telecom')).toBe(1)
  })
})

describe('traits FH', () => {
  it('jusqu\'à la liaison trouvée, sinon de longueur fixe', () => {
    const links = new Map([[beamKey(B[2]), { id: 99, lat: 48.12, lon: -1.5, dist: 7600, level: 'retour' as const }], [beamKey(B[3]), null]])
    const fc = fhFeatures(B, links, 2000)
    expect(fc.features).toHaveLength(2)
    const [lien, fixe] = fc.features
    expect(lien.properties).toMatchObject({ kind: 'lien', cible: 99, dist: 7600, level: 'retour', op: 0 })
    expect(lien.geometry.coordinates[1]).toEqual([-1.5, 48.12])
    expect(fixe.properties).toMatchObject({ kind: 'fixe', cible: null })
    const [lo, la] = fixe.geometry.coordinates[1]
    expect(distance(48.2, -1.5, la, lo)).toBeCloseTo(2000, 3)
  })
})
