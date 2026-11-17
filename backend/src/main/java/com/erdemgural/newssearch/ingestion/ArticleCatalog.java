package com.erdemgural.newssearch.ingestion;

import java.util.Collection;
import java.util.Map;
import java.util.UUID;

/**
 * Haber kayıtlarına diğer modüllerin erişim yolu. Haber tabloları bu modüle aittir; başka bir
 * modül (örneğin arama) haber bilgisine SQL yazarak değil bu arayüzle ulaşır.
 */
public interface ArticleCatalog {

    /**
     * Verilen kimliklerdeki haberlerin özet bilgilerini, kimliğe göre döner. Kayıtlı olmayan
     * veya gizlenmiş haberler sonuçta yer almaz (FG-AR-09). Ana görselin adresi imzalıdır ve
     * doğrudan arayüze verilebilir.
     */
    Map<UUID, ArticleSummary> findSummaries(Collection<UUID> articleIds);
}
