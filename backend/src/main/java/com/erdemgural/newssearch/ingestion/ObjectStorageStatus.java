package com.erdemgural.newssearch.ingestion;

/** Nesne depolamanın (MinIO) durumu; yönetim panosu için (FG-YP-12). */
public interface ObjectStorageStatus {

    /** Nesne depolama yanıt veriyor ve API'nin kimliğini tanıyorsa {@code true}. */
    boolean isAvailable();
}
