import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

const __dirname = path.dirname(fileURLToPath(import.meta.url))

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const isDev = mode === 'development'

  return {
    plugins: [react()],
    define: isDev
      ? {
          // Prebundled deps sometimes ship production React; Profiler needs development build.
          'process.env.NODE_ENV': JSON.stringify('development'),
        }
      : undefined,
    resolve: {
      dedupe: ['react', 'react-dom'],
      alias: {
        // react-plotly.js expects full plotly.js; map to the prebuilt min bundle.
        'plotly.js/dist/plotly': path.resolve(__dirname, 'node_modules/plotly.js-dist-min/plotly.min.js'),
      },
    },
    optimizeDeps: {
      include: ['react-plotly.js'],
      ...(isDev
        ? {
            esbuildOptions: {
              define: {
                'process.env.NODE_ENV': '"development"',
              },
            },
          }
        : {}),
    },
    server: {
      port: 5173,
      strictPort: false,
      open: false,
    },
  }
})
