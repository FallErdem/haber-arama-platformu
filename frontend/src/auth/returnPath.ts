/**
 * Girişten sonra dönülecek adres. Paylaşılan bir arama veya haber adresini açan, oturumu olmayan
 * kullanıcı Keycloak'ın giriş sayfasına gider; girişten sonra açmak istediği adrese döner.
 */

/** Giriş başlarken saklanacak adres: şu anki yol ve sorgu (`/articles/...?q=...`). */
export function currentReturnPath(): string {
  return window.location.pathname + window.location.search
}

/**
 * Girişten dönünce gidilecek güvenli adres. Değer yalnızca bu uygulamanın kendi yollarından biri
 * olabilir: `/` ile başlamalı, ancak `//` ile başlamamalıdır (`//kotu.site` tarayıcıda başka bir
 * siteye gider). Uymayan veya hiç olmayan değerde ana sayfaya dönülür; böylece giriş akışı başka
 * bir siteye yönlendirmek için kullanılamaz (açık yönlendirme).
 */
export function safeReturnPath(value: unknown): string {
  if (typeof value !== 'string' || !value.startsWith('/') || value.startsWith('//') || value.includes('\\')) {
    return '/'
  }
  // Dönüş sayfasının kendisine dönülmez; orada gösterilecek bir ekran yoktur.
  if (value.startsWith('/oidc-callback')) {
    return '/'
  }
  return value
}
