import { cn } from 'cn'

/**
 * Liste veya tablo yüklenirken satırların yerini tutan gri çubuklar (yönetim ekranları).
 */
export function ListSkeleton({ label, rows = 6, className }: { label: string; rows?: number; className?: string }) {
  return (
    <div role="status" className={className}>
      <span className="sr-only">{label}</span>
      <div
        aria-hidden
        className="animate-pulse divide-y divide-border border-y border-border motion-reduce:animate-none"
      >
        {Array.from({ length: rows }, (_, index) => (
          <div key={index} className="flex items-center gap-6 py-4">
            <div className="min-w-0 flex-1">
              <div className={cn('h-4 rounded-sm bg-muted', index % 2 === 0 ? 'w-2/5' : 'w-1/3')} />
              <div className="mt-2 h-3 w-1/5 rounded-sm bg-muted" />
            </div>
            <div className="hidden h-3 w-24 rounded-sm bg-muted sm:block" />
            <div className="h-6 w-16 rounded-md bg-muted" />
          </div>
        ))}
      </div>
    </div>
  )
}
