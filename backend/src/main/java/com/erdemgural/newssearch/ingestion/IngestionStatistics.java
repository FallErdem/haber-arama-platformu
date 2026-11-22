package com.erdemgural.newssearch.ingestion;

import java.time.Instant;

/** Yönetim panosunun haber ve besleme sayıları (FG-YP-12; API sözleşmesi 6.7). */
public interface IngestionStatistics {

    /**
     * Haber ve besleme sayıları ile işçinin son etkinliği.
     *
     * @param since "yakın zamanda toplanan" haberlerin alt sınırı (pano için son 24 saat)
     */
    IngestionSummary summarize(Instant since);
}
