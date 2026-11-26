/**
 * Uygulamanın logosu: bordo kare içinde serif "H" ve altında çizgi (gazete başlığının altındaki çizgi gibi).
 * Renkler temadan gelir; koyu temada kendiliğinden uyar. Yanında uygulamanın adı yazdığı için ekran okuyucuya
 * okunmaz. Sekme simgesi aynı çizimdir (public/favicon.svg).
 */
export function Logo({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 32 32" aria-hidden className={className}>
      <rect x="2" y="2" width="28" height="28" rx="6" className="fill-primary" />
      <text
        x="16"
        y="23"
        textAnchor="middle"
        fontSize="20"
        fontWeight="700"
        className="fill-primary-foreground font-heading"
      >
        H
      </text>
      <rect x="9" y="25" width="14" height="1.6" rx="0.8" className="fill-primary-foreground" />
    </svg>
  )
}
