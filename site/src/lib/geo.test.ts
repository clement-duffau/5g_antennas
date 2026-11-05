import { describe, expect, it } from 'vitest'
import { angleDiff, bearing, destination, distance, sector } from './geo'

describe('destination', () => {
  it('reste à la distance et au cap demandés', () => {
    for (const brg of [0, 45, 90, 135, 180, 270, 359]) {
      const [lon, lat] = destination(48.11, -1.68, brg, 5000)
      expect(distance(48.11, -1.68, lat, lon)).toBeCloseTo(5000, 3)
      expect(Math.abs(angleDiff(brg, bearing(48.11, -1.68, lat, lon)))).toBeLessThan(0.01)
    }
  })
  it('vers le nord, ne change que la latitude (1° ≈ 111,2 km)', () => {
    const [lon, lat] = destination(45, 2, 0, 111195)
    expect(lon).toBeCloseTo(2, 9)
    expect(lat).toBeCloseTo(46, 3)
  })
})

describe('angleDiff', () => {
  it('donne le plus court écart signé', () => {
    expect(angleDiff(350, 10)).toBe(20)
    expect(angleDiff(10, 350)).toBe(-20)
    expect(angleDiff(0, 180)).toBe(180)
    expect(angleDiff(90, 90)).toBe(0)
  })
})

describe('sector', () => {
  const ring = sector(48.11, -1.68, 120, 60, 1000, 24)
  it('est un anneau fermé : centre, 25 points d\'arc, centre', () => {
    expect(ring).toHaveLength(27)
    expect(ring[0]).toEqual([-1.68, 48.11])
    expect(ring[26]).toEqual(ring[0])
  })
  it('a ses points d\'arc à la bonne distance et dans l\'ouverture', () => {
    for (const [lon, lat] of ring.slice(1, -1)) {
      expect(distance(48.11, -1.68, lat, lon)).toBeCloseTo(1000, 3)
      expect(Math.abs(angleDiff(120, bearing(48.11, -1.68, lat, lon)))).toBeLessThanOrEqual(30 + 1e-6)
    }
    const mid = ring[13]
    expect(Math.abs(angleDiff(120, bearing(48.11, -1.68, mid[1], mid[0])))).toBeLessThan(1e-6)
  })
  it('traverse correctement le nord (azimut 0°)', () => {
    const r = sector(45, 2, 0, 40, 2000, 8)
    const first = bearing(45, 2, r[1][1], r[1][0]), last = bearing(45, 2, r[9][1], r[9][0])
    expect(angleDiff(0, first)).toBeCloseTo(-20, 4)
    expect(angleDiff(0, last)).toBeCloseTo(20, 4)
  })
})
