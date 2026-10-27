/** User-facing product identity (matches GitHub repo VECTORDB-BRAIN). */
export const PRODUCT_NAME = 'VECTORDB-BRAIN'

export const PRODUCT_TAGLINE =
  'Multi-layer reactive knowledge: Level 0 read-only sources, with queries and interaction shaping the middle memory layer.'

export const SECTION = {
  l0Corpus: 'Layer 0 · Corpus snapshot',
  reactiveQuery: 'Reactive layer · Last query',
  l0Ingest: 'Layer 0 · Ingest sources',
  queryExplore: 'Query layer · Explore & refine',
  l0FileTypes: 'Layer 0 · File types',
  l0TopSources: 'Layer 0 · Top sources',
  exploration3d: 'Exploration · 3D multivariate',
  queryResults: 'Query results · Memory signals',
  curationValidate: 'Curation gate · Dry-run validate',
} as const

export const NAV = {
  query: 'Query',
  ingest: 'Ingest',
  corpus: 'Corpus',
  analytics: 'Analytics',
} as const

export const ACTIONS = {
  runQuery: 'Run query',
  clearQuery: 'Clear',
  validateGate: 'Validate gate',
  ingestFile: 'Ingest file',
  ingestDirectory: 'Ingest directory',
} as const
