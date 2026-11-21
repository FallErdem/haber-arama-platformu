/**
 * Bellekteki bir dosyayı tarayıcıya indirtir. Dosyaya geçici bir adres (`blob:`) verilir, görünmeyen bir
 * bağlantıyla tıklanır ve adres serbest bırakılır; serbest bırakma bir sonraki tura bırakılır ki tarayıcı
 * indirmeyi başlatmış olsun.
 */
export function saveFile(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.append(link)
  link.click()
  link.remove()
  setTimeout(() => URL.revokeObjectURL(url), 0)
}
