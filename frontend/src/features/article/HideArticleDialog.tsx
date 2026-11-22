import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Label, Text, TextArea, TextField } from 'react-aria-components'
import { useTranslation } from 'react-i18next'
import { hideArticle } from '../../api/adminArticles'
import { useAccessToken } from '../../auth/accessToken'
import { Button } from '../../components/ui/button'
import {
  Dialog,
  DialogClose,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '../../components/ui/dialog'
import { adminErrorMessage } from '../admin/adminErrors'

/** API'nin sınırıyla aynı (API sözleşmesi 6.6). */
const MAX_REASON_LENGTH = 500

interface HideArticleDialogProps {
  articleId: string
  isOpen: boolean
  onOpenChange: (isOpen: boolean) => void
  /** Haber gizlendi: sayfa sonucu gösterir. */
  onHidden: () => void
}

/**
 * Haber gizleme penceresi (ekran akışları 4.4; FG-YP-09). Gerekçe yazılmadan onaylanamaz. Gizlenince arama ve
 * Kaydedilenler yeniden istenir; eski sonuçlarda gizlenen haber görünmesin.
 */
export function HideArticleDialog({ articleId, isOpen, onOpenChange, onHidden }: HideArticleDialogProps) {
  const { t } = useTranslation()
  const accessToken = useAccessToken()
  const queryClient = useQueryClient()
  const [reason, setReason] = useState('')

  const hide = useMutation({
    mutationFn: () => hideArticle(accessToken, articleId, reason.trim()),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['articles'] })
      void queryClient.invalidateQueries({ queryKey: ['saved-articles'] })
      onOpenChange(false)
      onHidden()
    },
  })

  return (
    <Dialog
      isOpen={isOpen}
      onOpenChange={(open) => {
        if (!open) hide.reset()
        onOpenChange(open)
      }}
      className="sm:max-w-md"
    >
      <DialogHeader>
        <DialogTitle>{t('article.hide.title')}</DialogTitle>
        <DialogDescription>{t('article.hide.text')}</DialogDescription>
      </DialogHeader>
      <form
        className="grid gap-3"
        onSubmit={(event) => {
          event.preventDefault()
          hide.mutate()
        }}
      >
        <TextField
          value={reason}
          onChange={setReason}
          maxLength={MAX_REASON_LENGTH}
          isRequired
          className="flex flex-col gap-1"
        >
          <Label className="text-sm font-medium">{t('article.hide.reason')}</Label>
          <TextArea
            rows={3}
            className="w-full rounded-lg border border-input bg-transparent px-2.5 py-1.5 text-base outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 md:text-sm"
          />
          <Text slot="description" className="text-xs text-muted-foreground">
            {t('article.hide.reasonHint')}
          </Text>
        </TextField>
        {hide.isError && (
          <p role="alert" className="text-sm text-destructive">
            {adminErrorMessage(hide.error, t)}
          </p>
        )}
        <DialogFooter>
          <DialogClose>{t('admin.cancel')}</DialogClose>
          <Button type="submit" variant="destructive" isDisabled={reason.trim() === '' || hide.isPending}>
            {t('article.hide.confirm')}
          </Button>
        </DialogFooter>
      </form>
    </Dialog>
  )
}
