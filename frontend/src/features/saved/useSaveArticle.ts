import { useMutation, useQueryClient } from '@tanstack/react-query'
import type { ArticleDetail, ArticleSearchResponse } from '../../api/articles'
import { saveArticle, unsaveArticle } from '../../api/savedArticles'
import { useAccessToken } from '../../auth/accessToken'

/**
 * Bir haberi kaydetme ve kayıttan çıkarma (FG-KO-01). Arama sonuçları, haber detayı ve Kaydedilenler
 * sayfası aynı kuralı kullanır.
 *
 * - Yer imi istek sürerken yeni durumunu gösterir (`mutation.variables`); istek başarısız olursa
 *   kendiliğinden eski durumuna döner, çağıran `isError` ile bir mesaj gösterir.
 * - İstek başarılı olunca önbellekteki arama sonuçlarında ve haber detayında haberin `saved` alanı
 *   güncellenir: sayfalar yeniden istenmeden doğru yer imini gösterir. Kaydedilenler listesi ise
 *   yeniden istenir; sırası ve sayısı değişmiştir.
 */
export function useSaveArticle(articleId: string, saved: boolean) {
  const accessToken = useAccessToken()
  const queryClient = useQueryClient()

  const mutation = useMutation({
    mutationFn: (save: boolean) => (save ? saveArticle(accessToken, articleId) : unsaveArticle(accessToken, articleId)),
    onSuccess: (_result, save) => {
      queryClient.setQueriesData<ArticleSearchResponse>({ queryKey: ['articles'] }, (old) =>
        old
          ? { ...old, items: old.items.map((item) => (item.id === articleId ? { ...item, saved: save } : item)) }
          : old,
      )
      queryClient.setQueryData<ArticleDetail>(['article', articleId], (old) => (old ? { ...old, saved: save } : old))
      // Döndürülen söz bitene kadar istek "sürüyor" sayılır: Kaydedilenler sayfasında çıkarılan haber,
      // liste yenilenip kaybolana kadar boş yer imiyle görünür.
      return queryClient.invalidateQueries({ queryKey: ['saved-articles'] })
    },
  })

  return {
    isSaved: mutation.isPending ? (mutation.variables ?? saved) : saved,
    setSaved: mutation.mutate,
    isPending: mutation.isPending,
    isError: mutation.isError,
  }
}
