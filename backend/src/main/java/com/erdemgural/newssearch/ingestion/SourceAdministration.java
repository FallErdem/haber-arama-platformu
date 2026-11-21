package com.erdemgural.newssearch.ingestion;

import java.util.List;
import java.util.UUID;

/**
 * Kaynak ve besleme yönetimi (FG-YP-04, FG-YP-06 – 08; API sözleşmesi 6.2 ve 6.3). Kaynak ve besleme
 * tabloları bu modüldedir; yönetim panelinin uç noktaları ({@code admin} modülü) bu arayüzü kullanır.
 *
 * <p>Değiştiren metotlar, kural ihlalinde {@code 409} durumlu bir {@code ApiException} fırlatır:
 * {@code VERSION_CONFLICT}, {@code ALREADY_EXISTS} veya {@code INVALID_STATE_TRANSITION}. Kayıt yoksa
 * {@code 404 NOT_FOUND}. Başarılı değişiklik de reddedilen deneme de audit log'a yazılır.
 */
public interface SourceAdministration {

    /** Kaynaklar, adlarına göre; sağlık özetleriyle. */
    List<SourceOverview> listSources();

    ManagedSource findSource(UUID sourceId);

    ManagedSource createSource(UUID adminId, NewSource source);

    ManagedSource updateSource(UUID adminId, UUID sourceId, SourceChange change);

    /**
     * Kaynağın etkin bütün beslemelerini hemen okunacak hale getirir (FG-YP-08); okumayı işçi yapar.
     *
     * @return okunacak besleme sayısı
     */
    int requestFetch(UUID adminId, UUID sourceId);

    /**
     * Kaynağın bütün içeriğinin (haberler ve görseller) silinmesini ister (FG-YP-14); silmeyi işçi yapar.
     * Geri alınamaz bir işlem olduğundan {@code confirmationCode} kaynağın kodu olmalıdır; değilse
     * {@code 400 VALIDATION_FAILED}. Kaynak etkinse {@code 409 SOURCE_MUST_BE_DISABLED}; silme zaten
     * sürüyorsa {@code 409 INVALID_STATE_TRANSITION}.
     *
     * @return silinecek haber sayısı
     */
    long requestPurge(UUID adminId, UUID sourceId, String confirmationCode);

    ManagedFeed createFeed(UUID adminId, UUID sourceId, NewFeed feed);

    ManagedFeed updateFeed(UUID adminId, UUID feedId, FeedChange change);
}
