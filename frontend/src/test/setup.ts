import '@testing-library/jest-dom/vitest'
import { cleanup } from '@testing-library/react'
import { afterEach } from 'vitest'
import '../i18n'

// Her testten sonra ekrana çizilenler temizlenir; testler birbirini etkilemez.
afterEach(() => {
  cleanup()
})
