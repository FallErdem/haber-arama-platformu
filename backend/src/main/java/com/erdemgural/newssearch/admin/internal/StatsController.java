package com.erdemgural.newssearch.admin.internal;

import com.erdemgural.newssearch.admin.internal.StatsResponse.Articles;
import com.erdemgural.newssearch.admin.internal.StatsResponse.Components;
import com.erdemgural.newssearch.admin.internal.StatsResponse.Feeds;
import com.erdemgural.newssearch.admin.internal.StatsResponse.SearchIndex;
import com.erdemgural.newssearch.admin.internal.StatsResponse.SourceArticles;
import com.erdemgural.newssearch.identity.UserAdministration;
import com.erdemgural.newssearch.ingestion.IngestionStatistics;
import com.erdemgural.newssearch.ingestion.IngestionSummary;
import com.erdemgural.newssearch.ingestion.ObjectStorageStatus;
import com.erdemgural.newssearch.search.SearchIndexStatus;
import java.time.Clock;
import java.time.Duration;
import java.util.LinkedHashMap;
import java.util.Map;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * Yönetim panosu (API sözleşmesi 6.7; FG-YP-12). Yalnızca {@code ADMIN} rolüne açıktır
 * ({@code /api/v1/admin/**}, güvenlik ayarı).
 *
 * <p>Her modül kendi verisini sayar; burada yalnızca birleştirilir. Hiçbir modül başka bir modülün tablosuna
 * bakmaz. Elasticsearch veya nesne depolama kapalıysa pano yine yanıt verir ve onları {@code DOWN} gösterir
 * (FOG-09).
 */
@RestController
@RequestMapping("/api/v1/admin/stats")
class StatsController {

    private static final Duration RECENT = Duration.ofHours(24);
    private static final String UP = "UP";
    private static final String DOWN = "DOWN";

    private final IngestionStatistics ingestionStatistics;
    private final UserAdministration userAdministration;
    private final SearchIndexStatus searchIndexStatus;
    private final ObjectStorageStatus objectStorageStatus;
    private final Clock clock;

    StatsController(
            IngestionStatistics ingestionStatistics,
            UserAdministration userAdministration,
            SearchIndexStatus searchIndexStatus,
            ObjectStorageStatus objectStorageStatus,
            Clock clock) {
        this.ingestionStatistics = ingestionStatistics;
        this.userAdministration = userAdministration;
        this.searchIndexStatus = searchIndexStatus;
        this.objectStorageStatus = objectStorageStatus;
        this.clock = clock;
    }

    @GetMapping
    StatsResponse stats() {
        IngestionSummary summary = ingestionStatistics.summarize(clock.instant().minus(RECENT));
        Map<String, Long> users = new LinkedHashMap<>();
        userAdministration.countByStatus().forEach((status, count) -> users.put(status.name(), count));

        return new StatsResponse(
                new Articles(
                        summary.totalArticles(),
                        summary.recentArticles(),
                        summary.bySource().stream()
                                .map(source -> new SourceArticles(
                                        source.code(), source.name(), source.total(), source.recent()))
                                .toList()),
                users,
                new Feeds(summary.enabledFeeds(), summary.failingFeeds(), summary.autoDisabledFeeds()),
                new SearchIndex(searchIndexStatus.pendingOutboxEvents()),
                new Components(
                        // Sayılar veritabanından okunduğuna göre veritabanı yanıt veriyordur; vermeseydi istek
                        // kimlik doğrulamasında (kullanıcı tablosu) başarısız olurdu.
                        UP,
                        searchIndexStatus.isAvailable() ? UP : DOWN,
                        objectStorageStatus.isAvailable() ? UP : DOWN,
                        summary.workerLastActivityAt()));
    }
}
