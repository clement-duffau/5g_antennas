import { describe, expect, it } from 'vitest'
import { candidatesInAxis, findLink, pointsBack, type LinkContext } from './fhLinks'
import { destination } from './geo'

// Origine O ; candidats placés par cap et distance depuis O.
const O = { lat: 48.1, lon: -1.6 }
const at = (brg: number, d: number) => { const [lon, lat] = destination(O.lat, O.lon, brg, d); return { lat, lon } }
const P = [
  O,                    // 0 : origine
  at(60, 10000),        // 1 : A, dans l'axe, FH du même exploitant pointant en retour
  at(60.5, 5000),       // 2 : B, dans l'axe, sans FH
  at(61.5, 8000),       // 3 : C, dans l'axe, FH du même exploitant, azimut ailleurs
  at(60, 70000),        // 4 : D, trop loin
  at(65, 9000),         // 5 : E, hors de l'axe (5°)
  at(240, 12000),       // 6 : F, dans l'axe opposé
]
const pts = { n: P.length, lat: P.map((p) => p.lat), lon: P.map((p) => p.lon) }

function ctx(fh: Record<number, number[]>, grp = 'Orange'): LinkContext {
  return {
    pts,
    hasFh: (i, g) => g === grp && i in fh,
    fhAzimuths: async (i, g) => (g === grp ? fh[i] ?? [] : []),
  }
}

describe('candidatesInAxis', () => {
  it('garde les supports à ≤ 2° et ≤ 60 km, triés par écart puis distance', () => {
    const c = candidatesInAxis(O.lat, O.lon, 60, pts, 0)
    expect(c.map((x) => x.i)).toEqual([1, 2, 3])
    expect(c[0].dist).toBeCloseTo(10000, 0)
    expect(c[1].err).toBeCloseTo(0.5, 3)
  })
  it('gère le passage par le nord', () => {
    const p = [O, at(359.5, 3000), at(1, 4000)]
    const c = candidatesInAxis(O.lat, O.lon, 0.5, { n: 3, lat: p.map((x) => x.lat), lon: p.map((x) => x.lon) }, 0)
    expect(c.map((x) => x.i).sort()).toEqual([1, 2])
  })
})

describe('pointsBack', () => {
  it('reconnaît un azimut qui vise l\'origine à ± 5°', () => {
    expect(pointsBack(P[1].lat, P[1].lon, O.lat, O.lon, [240.1])).toBe(true)
    expect(pointsBack(P[1].lat, P[1].lon, O.lat, O.lon, [246])).toBe(false)
  })
})

describe('findLink', () => {
  it('préfère le support qui pointe en retour', async () => {
    const l = await findLink(0, 60, 'Orange', ctx({ 1: [240.1], 3: [10] }))
    expect(l).toMatchObject({ i: 1, level: 'retour' })
  })
  it('choisit le retour même s\'il est moins bien aligné', async () => {
    const l = await findLink(0, 60, 'Orange', ctx({ 1: [10], 3: [241.5] }))
    expect(l).toMatchObject({ i: 3, level: 'retour' })
  })
  it('à défaut de retour, garde le support du même exploitant le mieux aligné', async () => {
    const l = await findLink(0, 60, 'Orange', ctx({ 1: [10], 3: [10] }))
    expect(l).toMatchObject({ i: 1, level: 'exploitant' })
  })
  it('ignore les supports sans FH du même exploitant', async () => {
    expect(await findLink(0, 60, 'Orange', ctx({}))).toBeNull()
    expect(await findLink(0, 60, 'SFR', ctx({ 1: [240] }, 'Orange'))).toBeNull()
  })
})
