/** Structure de stats.json (voir pipeline/stats.py). */
export interface Meta {
  extraction: string
  generation: string
  perimetre: string
  source: { titre?: string; licence?: string; page?: string; archive?: string; url?: string; publication?: string; extractions_disponibles?: number }
}

export interface SupportRow {
  sup_id: number; hauteur: number | null; nature: string | null; proprietaire: string | null
  commune: string; insee: string; dep: string; lat: number; lon: number; adresse: string | null
  groupes: string[]; n_groupes: number; n_emetteurs: number
}

export interface DepRow {
  dep: string; nom: string; region: string; supports: number; sites_mobiles: number; sites_5g: number
  sites_4_operateurs: number; emetteurs: number; hauteur_moyenne: number; hauteur_max: number
  population: number; surface_km2: number; supports_par_100km2: number; supports_par_10k_hab: number; part_5g: number
}

export interface CommuneRow {
  insee: string; nom: string; dep: string; supports: number; sites_5g: number; emetteurs: number
  population: number; surface_km2: number; supports_par_km2: number; supports_par_10k_hab: number
}

export interface SystemeRow {
  systeme: string; famille: string; generation: string | null; bande: string | null; description: string | null
  emetteurs: number; supports: number; debut_deploiement: number | null
  [op: string]: string | number | null
}

export interface Stats {
  meta: Meta
  totaux: Record<'supports' | 'stations' | 'antennes' | 'emetteurs' | 'bandes' | 'exploitants' | 'systemes' | 'communes' | 'supports_mobiles' | 'supports_5g', number>
  operateurs_mobiles: string[]
  operateurs: { groupe: string; categorie: string; stations: number; supports: number; emetteurs: number; '2G': number; '3G': number; '4G': number; '5G': number; libelles_anfr: string[] }[]
  familles: { famille: string; emetteurs: number; supports: number; exploitants: number }[]
  systemes: SystemeRow[]
  sites_operateur_systeme: { groupe: string; systeme: string; generation: string; bande: string; sites: number; emetteurs: number }[]
  sites_operateur_generation: { groupe: string; generation: string; sites: number }[]
  spectre_national: { groupe: string; systeme: string; generation: string; f_deb: number; f_fin: number; n: number; part: number }[]
  departements: DepRow[]
  communes_top: CommuneRow[]
  communes_densite_km2: CommuneRow[]
  communes_par_habitant: CommuneRow[]
  plus_hauts: SupportRow[]
  plus_exploitants: SupportRow[]
  plus_emetteurs: SupportRow[]
  partage_mobile: { operateurs: number; supports: number }[]
  natures: { nature: string; supports: number; hauteur_moyenne: number | null }[]
  proprietaires: { proprietaire: string; supports: number }[]
  hauteurs: { de: number; supports: number }[]
  deploiement: { annee: number; groupe: string; generation: string; emetteurs: number; nouveaux_sites: number }[]
  deploiement_systemes: { annee: number; systeme: string; emetteurs: number }[]
  antennes: {
    types: { type: string; antennes: number }[]
    azimuts: { de: number; antennes: number }[]
    rayonnement: { rayonnement: string; antennes: number }[]
  }
  qualite: Record<string, number>
}
