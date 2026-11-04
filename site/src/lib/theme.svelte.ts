/** Thème : sombre par défaut, préférence mémorisée (localStorage, si disponible). */
type Theme = 'dark' | 'light'

function initial(): Theme {
  try {
    const saved = localStorage.getItem('theme')
    if (saved === 'dark' || saved === 'light') return saved
  } catch { /* stockage indisponible */ }
  return 'dark'
}

export const theme = $state({ value: initial() })

export function applyTheme() {
  document.documentElement.dataset.theme = theme.value
  try { localStorage.setItem('theme', theme.value) } catch { /* ignoré */ }
}
