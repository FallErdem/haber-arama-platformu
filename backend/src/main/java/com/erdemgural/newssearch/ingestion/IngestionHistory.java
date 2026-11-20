package com.erdemgural.newssearch.ingestion;

import com.erdemgural.newssearch.web.PageParameters;
import com.erdemgural.newssearch.web.PageResponse;

/** Toplama geçmişi (FG-YP-05; API sözleşmesi 6.5). Kayıtları işçi yazar; API yalnızca okur. */
public interface IngestionHistory {

    /** Okumalar, başlangıç zamanına göre yeniden eskiye. */
    PageResponse<IngestionRun> list(IngestionRunFilter filter, PageParameters page);
}
