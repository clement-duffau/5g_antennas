/** Couleurs par entité (jamais par rang) : un opérateur garde sa couleur quel que soit le filtre. */
export const MOBILE_OPS = ['Orange', 'Bouygues Telecom', 'SFR', 'Free'] as const
export type MobileOp = (typeof MOBILE_OPS)[number]

const OP_VAR: Record<string, string> = {
  Orange: 'var(--op-orange)',
  'Bouygues Telecom': 'var(--op-bouygues)',
  SFR: 'var(--op-sfr)',
  Free: 'var(--op-free)',
}
export const opColor = (op: string) => OP_VAR[op] ?? 'var(--op-autre)'

export const GENERATIONS = ['2G', '3G', '4G', '5G'] as const
const GEN_VAR: Record<string, string> = {
  '2G': 'var(--gen-2g)', '3G': 'var(--gen-3g)', '4G': 'var(--gen-4g)', '5G': 'var(--gen-5g)',
}
export const genColor = (g: string) => GEN_VAR[g] ?? 'var(--op-autre)'

/** Index 0..5 de la rampe séquentielle pour une valeur t dans [0, 1]. */
export const seqColor = (t: number) => `var(--seq-${Math.max(0, Math.min(5, Math.round(t * 5)))})`
