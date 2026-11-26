/*
 * Okuma geçmişi: kullanıcının açtığı son haberler (en yenisi başta). Tarayıcıda saklanır; sunucuya gitmez. Bu
 * yüzden yalnızca o tarayıcıda görünür (telefonda açılan haber bilgisayarda görünmez). Kayıt kullanıcıya göre
 * ayrıdır: aynı tarayıcıda başka biri giriş yaparsa bu geçmişi görmez.
 *
 * Haber sayfası haberi buraya ekler; yan sütun dinler ve haber açıldığı anda güncellenir (useSyncExternalStore).
 */
import { useSyncExternalStore } from 'react'

/** Geçmişte tutulan bir haber: listede göstermeye yetecek kadar bilgi. */
export interface ReadEntry {
  id: string
  title: string
  sourceName: string
  language: string
  /** Haberin açıldığı an (ISO). */
  readAt: string
}

/** Geçmişte tutulan en fazla haber sayısı. */
const MAX_ENTRIES = 9
const KEY_PREFIX = 'readingHistory:'

const listeners = new Set<() => void>()
/** Son okunan kayıt: aynı metin için aynı dizi döner (useSyncExternalStore her seferinde aynı nesneyi bekler). */
let cached: { key: string; raw: string | null; entries: ReadEntry[] } | null = null

function keyFor(userId: string): string {
  return KEY_PREFIX + userId
}

function isEntry(value: unknown): value is ReadEntry {
  const entry = value as ReadEntry
  return (
    typeof entry === 'object' &&
    entry !== null &&
    typeof entry.id === 'string' &&
    typeof entry.title === 'string' &&
    typeof entry.sourceName === 'string' &&
    typeof entry.language === 'string' &&
    typeof entry.readAt === 'string'
  )
}

/** Kullanıcının geçmişi. Kayıt yoksa, bozuksa veya tarayıcı depolamayı engelliyorsa boş liste. */
export function getHistory(userId: string): ReadEntry[] {
  const key = keyFor(userId)
  let raw: string | null = null
  try {
    raw = localStorage.getItem(key)
  } catch {
    // Depolama engelli: geçmiş tutulmaz.
  }
  if (cached && cached.key === key && cached.raw === raw) {
    return cached.entries
  }
  let entries: ReadEntry[] = []
  try {
    const parsed: unknown = raw ? JSON.parse(raw) : []
    entries = Array.isArray(parsed) ? parsed.filter(isEntry).slice(0, MAX_ENTRIES) : []
  } catch {
    // Bozuk kayıt: boş geçmiş.
  }
  cached = { key, raw, entries }
  return entries
}

function save(userId: string, entries: ReadEntry[]): void {
  try {
    localStorage.setItem(keyFor(userId), JSON.stringify(entries))
  } catch {
    // Depolama engelli: geçmiş tutulmaz.
  }
  listeners.forEach((listener) => listener())
}

/** Açılan haberi geçmişin başına ekler; daha önce açıldıysa eski kaydı kaldırır. */
export function rememberArticle(userId: string, entry: Omit<ReadEntry, 'readAt'>): void {
  const others = getHistory(userId).filter((existing) => existing.id !== entry.id)
  save(userId, [{ ...entry, readAt: new Date().toISOString() }, ...others].slice(0, MAX_ENTRIES))
}

/** Geçmişi siler. */
export function clearHistory(userId: string): void {
  save(userId, [])
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener)
  // Başka bir sekmede açılan haber de bu sekmedeki listeye yansır.
  const onStorage = (event: StorageEvent) => {
    if (event.key?.startsWith(KEY_PREFIX)) listener()
  }
  window.addEventListener('storage', onStorage)
  return () => {
    listeners.delete(listener)
    window.removeEventListener('storage', onStorage)
  }
}

/** Kullanıcının geçmişi; değişince bileşen yeniden çizilir. */
export function useReadingHistory(userId: string): ReadEntry[] {
  return useSyncExternalStore(subscribe, () => getHistory(userId))
}
