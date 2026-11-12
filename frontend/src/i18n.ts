import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'
import en from './locales/en.json'
import tr from './locales/tr.json'

// Arayüz metinleri bileşenlere yazılmaz, dil dosyalarından okunur (FOG-31).
// Yeni bir dil eklemek için bir dosya ve aşağıya bir satır yeterlidir.
void i18n.use(initReactI18next).init({
  resources: {
    tr: { translation: tr },
    en: { translation: en },
  },
  lng: 'tr',
  fallbackLng: 'tr',
  // React metinleri ekrana yazarken zaten güvenli hale getirir; ikinci kez gerekmez.
  interpolation: { escapeValue: false },
})

export default i18n
