import { describe, expect, it } from 'vitest'
import { beams, decode, drawableRows, encode, rowKey } from './azimuthSelection'
import type { SupportDetail } from './detail'

describe('URL', () => {
  it('encode et décode sans perte, valeurs par défaut omises', () => {
    const st = { list: [{ id: 513212, rows: null }, { id: 2841493, rows: ['0422750123_LTE800', '0422750123_5GNR3500'] }], len: 1000, ap: 65 }
    const p = encode(st)
    expect(p).toEqual({ az: '513212,2841493.0422750123_LTE800.0422750123_5GNR3500', azl: null, azo: null })
    expect(decode({ az: p.az! })).toEqual(st)
  })
  it('garde longueur et ouverture, bornées', () => {
    expect(decode({ az: '1', azl: '2500', azo: '30' })).toMatchObject({ len: 2500, ap: 30 })
    expect(decode({ az: '1', azl: '99999', azo: '1' })).toMatchObject({ len: 5000, ap: 10 })
  })
  it('ignore les éléments invalides ou en double', () => {
    expect(decode({ az: 'abc,12,12,-3,,7.bad.0350000001_FH', azl: 'x' })).toEqual({
      list: [{ id: 12, rows: null }, { id: 7, rows: ['0350000001_FH'] }], len: 1000, ap: 65,
    })
  })
  it('n\'écrit rien sans support', () => {
    expect(encode({ list: [], len: 2000, ap: 30 })).toEqual({ az: null, azl: null, azo: null })
  })
})

// Support fictif : Orange (LTE 800 trisectoriel + FH), SFR (5G sur une antenne partagée en azimut), PMR non directionnelle.
const D: SupportDetail = {
  lat: 48.1, lon: -1.6, h: 30, nat: 'Pylône', tpo: null, adr: null, cp: null, insee: '35238', com: 'Rennes',
  st: [
    {
      sta: '0350000001', exp: 'ORANGE', grp: 'Orange', impl: null, serv: null, mod: null,
      emr: [
        { s: 'LTE 800', d: '2015-01-01', b: [], a: [1, 2, 3], n: 3 },
        { s: 'LTE 800', d: '2020-01-01', b: [], a: [1], n: 1 },
        { s: 'FH', d: null, b: [], a: [4], n: 1 },
      ],
      ant: [
        { id: 1, t: null, dim: null, r: 'D', az: 0, h: 30 }, { id: 2, t: null, dim: null, r: 'D', az: 120, h: 30 },
        { id: 3, t: null, dim: null, r: 'D', az: 240, h: 30 }, { id: 4, t: null, dim: null, r: 'D', az: 77.6, h: 32 },
        { id: 9, t: null, dim: null, r: 'D', az: 300, h: 10 },
      ],
    },
    {
      sta: '0350000002', exp: 'SFR', grp: 'SFR', impl: null, serv: null, mod: null,
      emr: [{ s: '5G NR 3500', d: null, b: [], a: [10, 11], n: 2 }, { s: 'PMR', d: null, b: [], a: [12], n: 1 }],
      ant: [
        { id: 10, t: null, dim: null, r: 'D', az: 120.2, h: 28 }, { id: 11, t: null, dim: null, r: 'D', az: 119.8, h: 28 },
        { id: 12, t: null, dim: null, r: 'N', az: null, h: 28 },
      ],
    },
  ],
}
const fam = (s: string) => (s === 'FH' ? 'Faisceau hertzien' : s === 'PMR' ? 'PMR' : 'Mobile')

describe('lignes et antennes', () => {
  it('liste les lignes station × système cochables', () => {
    expect(drawableRows(D).map((r) => r.key)).toEqual(['0350000001_LTE800', '0350000001_FH', '0350000002_5GNR3500'])
  })
  it('tout le support : dédoublonne par exploitant et azimut, distingue le FH', () => {
    const b = beams(D, null, fam)
    expect(b.filter((x) => !x.fh).map((x) => `${x.grp}:${Math.round(x.az)}`).sort())
      .toEqual(['Orange:0', 'Orange:120', 'Orange:240', 'Orange:300', 'SFR:120'])
    expect(b.filter((x) => x.fh)).toEqual([{ grp: 'Orange', az: 77.6, fh: true }])
  })
  it('sélection partielle : seulement les antennes des lignes cochées', () => {
    const b = beams(D, [rowKey('0350000002', '5G NR 3500')], fam)
    expect(b).toEqual([{ grp: 'SFR', az: 120.2, fh: false }])
  })
})
