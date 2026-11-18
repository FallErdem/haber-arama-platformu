import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { AuthProvider } from 'react-oidc-context'
import App from './App.tsx'
import { shouldRetry } from './api/client'
import { oidcConfig } from './auth/oidcConfig'
import './i18n'
import './index.css'

// Bütün API isteklerinin ortak ayarı: sunucunun verdiği hata yeniden denenmez (bkz. shouldRetry).
const queryClient = new QueryClient({ defaultOptions: { queries: { retry: shouldRetry } } })

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <AuthProvider {...oidcConfig}>
      <QueryClientProvider client={queryClient}>
        <App />
      </QueryClientProvider>
    </AuthProvider>
  </StrictMode>,
)
