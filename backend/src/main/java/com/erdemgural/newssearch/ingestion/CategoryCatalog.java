package com.erdemgural.newssearch.ingestion;

import java.time.Duration;
import java.util.Map;

/** Kategori bilgilerine diğer modüllerin erişim yolu. */
public interface CategoryCatalog {

    /**
     * Süreli kategoriler ve süreleri, kategori koduna göre (FG-AR-12). Süreli bir kategori (Son
     * Dakika) yalnızca bu süre içinde yayımlanmış haberlerde geçerlidir; süresi olmayan
     * kategoriler sonuçta yer almaz.
     */
    Map<String, Duration> timeWindows();
}
