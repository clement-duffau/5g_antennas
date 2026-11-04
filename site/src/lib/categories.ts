/** Modes de coloration de la carte : chaque support reçoit une catégorie par mode. */
import { famBit, popcount, type SupportIndex } from './supports'

export interface Category { key: number; label: string; color: string }
export interface ColorMode { id: 'techno' | 'ops' | 'hauteur'; label: string; prop: string; categories: Category[] }

export const COLOR_MODES: ColorMode[] = [
  {
    id: 'techno', label: 'Technologie la plus récente', prop: 't',
    categories: [
      { key: 0, label: '5G', color: 'var(--cat-1)' },
      { key: 1, label: '4G', color: 'var(--cat-2)' },
      { key: 2, label: '2G / 3G seulement', color: 'var(--cat-3)' },
      { key: 3, label: 'Radio et télévision', color: 'var(--cat-4)' },
      { key: 4, label: 'Faisceaux hertziens', color: 'var(--cat-5)' },
      { key: 5, label: 'PMR et réseaux privés', color: 'var(--cat-6)' },
      { key: 6, label: 'Autres', color: 'var(--cat-7)' },
    ],
  },
  {
    id: 'ops', label: 'Opérateurs mobiles présents', prop: 'o',
    categories: [
      { key: 0, label: 'Aucun', color: 'var(--cat-7)' },
      { key: 1, label: '1 opérateur', color: 'var(--seq-1)' },
      { key: 2, label: '2 opérateurs', color: 'var(--seq-2)' },
      { key: 3, label: '3 opérateurs', color: 'var(--seq-4)' },
      { key: 4, label: '4 opérateurs', color: 'var(--seq-5)' },
    ],
  },
  {
    id: 'hauteur', label: 'Hauteur du support', prop: 'h',
    categories: [
      { key: 0, label: 'moins de 15 m', color: 'var(--seq-1)' },
      { key: 1, label: '15 à 30 m', color: 'var(--seq-2)' },
      { key: 2, label: '30 à 45 m', color: 'var(--seq-3)' },
      { key: 3, label: '45 à 80 m', color: 'var(--seq-4)' },
      { key: 4, label: '80 m et plus', color: 'var(--seq-5)' },
      { key: 5, label: 'inconnue', color: 'var(--cat-7)' },
    ],
  },
]

export function categorize(s: SupportIndex) {
  const radio = famBit(s, 'Radiodiffusion')
  const fh = famBit(s, 'Faisceau hertzien')
  const pmr = famBit(s, 'PMR') | famBit(s, 'Réseau privé') | famBit(s, 'Ferroviaire')
  const t = new Uint8Array(s.n), o = new Uint8Array(s.n), h = new Uint8Array(s.n)
  for (let i = 0; i < s.n; i++) {
    const g = s.gen[i], f = s.fam[i]
    t[i] = g & 8 ? 0 : g & 4 ? 1 : g & 3 ? 2 : f & radio ? 3 : f & fh ? 4 : f & pmr ? 5 : 6
    o[i] = popcount(s.ops[i] & 15)
    const hh = s.h[i]
    h[i] = Number.isNaN(hh) ? 5 : hh < 15 ? 0 : hh < 30 ? 1 : hh < 45 ? 2 : hh < 80 ? 3 : 4
  }
  return { t, o, h }
}

/** Résout une couleur CSS (var(--x)) en valeur concrète pour MapLibre. */
export function resolveColor(css: string): string {
  const m = css.match(/^var\((--[\w-]+)\)$/)
  if (!m) return css
  return getComputedStyle(document.documentElement).getPropertyValue(m[1]).trim() || '#888'
}
