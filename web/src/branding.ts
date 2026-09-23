/** User-facing product identity (matches GitHub repo VECTORDB-BRAIN). */
export const PRODUCT_NAME = 'VECTORDB-BRAIN'

export const PRODUCT_TAGLINE =
  'Multi-layer reactive knowledge: Layer 1 read-only sources, Layer 2 interaction memory, Layer 3 idle relationships.'

export const SECTION = {
  l1Corpus: 'Layer 1 · Corpus snapshot',
  reactiveQuery: 'Reactive layer · Last query',
  l1Ingest: 'Layer 1 · Ingest sources',
  queryExplore: 'Query layer · Explore & refine',
  l1FileTypes: 'Layer 1 · File types',
  l1TopSources: 'Layer 1 · Top sources',
  exploration3d: 'Exploration · 3D multivariate',
  queryResults: 'Query results · Memory signals',
  layer1Hits: 'Layer 1 · Semantic hits',
  layer2Boosted: 'Layer 2 · Interaction-boosted',
  layer3Relations: 'Layer 3 · Dreaming relations',
} as const

export const ACTIONS = {
  runQuery: 'Run query',
  clearQuery: 'Clear',
} as const
