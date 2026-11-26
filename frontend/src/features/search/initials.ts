/** Birden fazla kelimeyse ilk ikisinin baş harfleri, tek kelimeyse ilk iki harfi; Türkçe büyük harf kuralıyla. */
export function initialsOf(name: string): string {
  const words = name.trim().split(/\s+/).filter(Boolean)
  const letters = words.length > 1 ? words[0][0] + words[1][0] : (words[0] ?? '').slice(0, 2)
  return letters.toLocaleUpperCase('tr-TR')
}
