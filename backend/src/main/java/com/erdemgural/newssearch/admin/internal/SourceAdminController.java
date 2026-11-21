package com.erdemgural.newssearch.admin.internal;

import com.erdemgural.newssearch.identity.CurrentUser;
import com.erdemgural.newssearch.ingestion.ManagedFeed;
import com.erdemgural.newssearch.ingestion.ManagedSource;
import com.erdemgural.newssearch.ingestion.NewFeed;
import com.erdemgural.newssearch.ingestion.NewSource;
import com.erdemgural.newssearch.ingestion.SourceAdministration;
import com.erdemgural.newssearch.ingestion.SourceChange;
import com.erdemgural.newssearch.ingestion.SourceOverview;
import com.erdemgural.newssearch.web.FieldError.Code;
import com.erdemgural.newssearch.web.ListResponse;
import java.time.ZoneId;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import java.util.regex.Pattern;
import org.springframework.http.HttpStatus;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;
import tools.jackson.databind.JsonNode;

/**
 * Kaynak yönetimi (API sözleşmesi 6.2 ve 6.3; FG-YP-04, FG-YP-06, FG-YP-08). Yalnızca {@code ADMIN} rolüne
 * açıktır. Kurallar {@code ingestion} modülündedir; burada istek okunur ve biçimi doğrulanır.
 *
 * <p>Yanıtlar {@code ingestion} modülünün dışa açık kayıtlarıdır ({@link ManagedSource} gibi): bu kayıtlar
 * yalnızca yönetim paneli için var ve alanları zaten yanıtın biçimindedir; ayrı bir yanıt kaydı yalnızca
 * alanları kopyalardı.
 */
@RestController
@RequestMapping("/api/v1/admin/sources")
class SourceAdminController {

    /** Kaynak kodu: büyük harfle başlar; büyük harf, rakam ve alt çizgi ({@code TRT}, {@code GLOBALVOICES}). */
    private static final Pattern CODE = Pattern.compile("[A-Z][A-Z0-9_]{1,39}");

    private static final int MAX_CODE_LENGTH = 40;

    /** NYT okuyucusu ({@code NYT_TOP_STORIES}) İ-13 ile gelecek; işçi şimdilik yalnızca bunları okuyabilir. */
    private static final List<String> READER_TYPES = List.of("RSS", "ATOM");

    private static final List<String> LANGUAGES = List.of("tr", "en");

    static final int MAX_NAME_LENGTH = 100;
    static final int MAX_URL_LENGTH = 2000;
    private static final int MAX_TEXT_LENGTH = 500;
    private static final int MAX_REQUEST_INTERVAL_SECONDS = 3600;
    private static final int MAX_DAILY_REQUEST_LIMIT = 1_000_000;

    private final SourceAdministration sourceAdministration;

    SourceAdminController(SourceAdministration sourceAdministration) {
        this.sourceAdministration = sourceAdministration;
    }

    @GetMapping
    ListResponse<SourceOverview> list() {
        return new ListResponse<>(sourceAdministration.listSources());
    }

    @GetMapping("/{id}")
    ManagedSource detail(@PathVariable UUID id) {
        return sourceAdministration.findSource(id);
    }

    /** Kaynak devre dışı olarak eklenir; beslemeleri eklendikten sonra etkinleştirilir. */
    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    ManagedSource create(@AuthenticationPrincipal CurrentUser admin, @RequestBody JsonNode body) {
        JsonFields fields = new JsonFields(body);
        String code = fields.requiredText("code", MAX_CODE_LENGTH);
        if (code != null && !CODE.matcher(code).matches()) {
            fields.addError("code", Code.INVALID_VALUE);
        }
        String name = fields.requiredText("name", MAX_NAME_LENGTH);
        String homepageUrl = fields.requiredText("homepageUrl", MAX_URL_LENGTH);
        fields.requireHttpUrl("homepageUrl", homepageUrl);
        String readerType = fields.requiredText("readerType", 40);
        fields.requireOneOf("readerType", readerType, READER_TYPES);
        String language = fields.requiredText("language", 2);
        fields.requireOneOf("language", language, LANGUAGES);
        Integer requestIntervalSeconds =
                fields.requiredInteger("requestIntervalSeconds", 1, MAX_REQUEST_INTERVAL_SECONDS);
        Integer dailyRequestLimit = fields.optionalInteger("dailyRequestLimit", 1, MAX_DAILY_REQUEST_LIMIT);
        String license = fields.optionalText("license", MAX_TEXT_LENGTH);
        String attributionText = fields.optionalText("attributionText", MAX_TEXT_LENGTH);
        String feedTimeZone = fields.optionalText("feedTimeZone", 64);
        requireTimeZone(fields, feedTimeZone);
        fields.throwIfInvalid();

        return sourceAdministration.createSource(
                admin.id(),
                new NewSource(
                        code,
                        name,
                        homepageUrl,
                        readerType,
                        language,
                        requestIntervalSeconds,
                        dailyRequestLimit,
                        license,
                        attributionText,
                        feedTimeZone));
    }

    /**
     * Kaynağı düzenler, etkinleştirir veya devre dışı bırakır. {@code code}, {@code readerType} ve
     * {@code language} değiştirilemez: kaynağın mevcut haberleri ve kategori eşlemeleriyle tutarsızlık
     * oluşturur (sözleşme 6.2); gönderilirlerse istek reddedilir.
     */
    @PatchMapping("/{id}")
    ManagedSource update(
            @AuthenticationPrincipal CurrentUser admin, @PathVariable UUID id, @RequestBody JsonNode body) {
        JsonFields fields = new JsonFields(body);
        for (String immutable : List.of("code", "readerType", "language")) {
            if (fields.has(immutable)) {
                fields.addError(immutable, Code.INVALID_VALUE);
            }
        }
        String name = fields.text("name", MAX_NAME_LENGTH);
        String homepageUrl = fields.text("homepageUrl", MAX_URL_LENGTH);
        fields.requireHttpUrl("homepageUrl", homepageUrl);
        Integer requestIntervalSeconds = fields.integer("requestIntervalSeconds", 1, MAX_REQUEST_INTERVAL_SECONDS);
        Optional<Integer> dailyRequestLimit = fields.nullableInteger("dailyRequestLimit", 1, MAX_DAILY_REQUEST_LIMIT);
        Optional<String> license = fields.nullableText("license", MAX_TEXT_LENGTH);
        Optional<String> attributionText = fields.nullableText("attributionText", MAX_TEXT_LENGTH);
        Optional<String> feedTimeZone = fields.nullableText("feedTimeZone", 64);
        if (feedTimeZone != null) {
            feedTimeZone.ifPresent(zone -> requireTimeZone(fields, zone));
        }
        Boolean enabled = fields.bool("enabled");
        Integer version = fields.requiredInteger("version", 0, Integer.MAX_VALUE);
        fields.throwIfInvalid();

        return sourceAdministration.updateSource(
                admin.id(),
                id,
                new SourceChange(
                        name,
                        homepageUrl,
                        requestIntervalSeconds,
                        dailyRequestLimit,
                        license,
                        attributionText,
                        feedTimeZone,
                        enabled,
                        version));
    }

    /** Elle toplama (FG-YP-08): okumayı işçi yapar; istek kabul edildi anlamında 202 döner (sözleşme 2.5). */
    @PostMapping("/{id}/fetch")
    @ResponseStatus(HttpStatus.ACCEPTED)
    FetchResponse fetch(@AuthenticationPrincipal CurrentUser admin, @PathVariable UUID id) {
        return new FetchResponse(sourceAdministration.requestFetch(admin.id(), id));
    }

    /**
     * Kaynağın bütün içeriğinin silinmesini ister (FG-YP-14); silmeyi işçi yapar, 202 döner. Gövde onay
     * olarak kaynağın kodunu içerir: {@code { "confirmationCode": "TRT" }}.
     */
    @PostMapping("/{id}/purge")
    @ResponseStatus(HttpStatus.ACCEPTED)
    PurgeResponse purge(@AuthenticationPrincipal CurrentUser admin, @PathVariable UUID id, @RequestBody JsonNode body) {
        JsonFields fields = new JsonFields(body);
        String confirmationCode = fields.requiredText("confirmationCode", MAX_CODE_LENGTH);
        fields.throwIfInvalid();

        return new PurgeResponse(sourceAdministration.requestPurge(admin.id(), id, confirmationCode));
    }

    /** Kaynağa besleme ekler; besleme kaynak etkinse hemen okunur. */
    @PostMapping("/{id}/feeds")
    @ResponseStatus(HttpStatus.CREATED)
    ManagedFeed createFeed(
            @AuthenticationPrincipal CurrentUser admin, @PathVariable UUID id, @RequestBody JsonNode body) {
        JsonFields fields = new JsonFields(body);
        String name = fields.requiredText("name", MAX_NAME_LENGTH);
        String url = fields.requiredText("url", MAX_URL_LENGTH);
        fields.requireHttpUrl("url", url);
        String defaultCategoryCode = fields.optionalText("defaultCategoryCode", 40);
        Boolean useItemCategories = fields.requiredBool("useItemCategories");
        Integer fetchIntervalMinutes =
                fields.requiredInteger("fetchIntervalMinutes", 1, FeedAdminController.MAX_FETCH_INTERVAL_MINUTES);
        fields.throwIfInvalid();

        return sourceAdministration.createFeed(
                admin.id(), id, new NewFeed(name, url, defaultCategoryCode, useItemCategories, fetchIntervalMinutes));
    }

    /**
     * Saat dilimi adı tanınıyor mu ({@code Europe/Istanbul}). İşçi de aynı adları (IANA saat dilimi
     * veritabanı) tanır; tanınmayan bir ad beslemenin okunmasını başarısız yapardı.
     */
    private static void requireTimeZone(JsonFields fields, String zone) {
        if (zone != null && !ZoneId.getAvailableZoneIds().contains(zone)) {
            fields.addError("feedTimeZone", Code.INVALID_VALUE);
        }
    }

    /** @param feedCount okunacak besleme sayısı (kaynağın etkin beslemeleri) */
    record FetchResponse(int feedCount) {}

    /** @param articleCount silinecek haber sayısı (istek anında) */
    record PurgeResponse(long articleCount) {}
}
