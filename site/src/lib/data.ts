/** Chargement des fichiers générés par le pipeline (site/public/data), avec cache mémoire. */
const cache = new Map<string, Promise<unknown>>()

export function loadJSON<T>(name: string): Promise<T> {
  if (!cache.has(name)) {
    const p = fetch(`${import.meta.env.BASE_URL}data/${name}`).then((r) => {
      if (!r.ok) throw new Error(`${name} : HTTP ${r.status}`)
      return r.json()
    })
    p.catch(() => cache.delete(name))
    cache.set(name, p)
  }
  return cache.get(name) as Promise<T>
}
