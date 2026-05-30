import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import { UiLogOverlay } from './logging/UiLogOverlay.tsx'
import { uiLogInteraction, UI_LOGGING_ENABLED } from './logging/uiLogger.ts'

if (UI_LOGGING_ENABLED) {
  uiLogInteraction('app.boot', 'VECTORDB-BRAIN web client started')
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
    <UiLogOverlay />
  </StrictMode>,
)
