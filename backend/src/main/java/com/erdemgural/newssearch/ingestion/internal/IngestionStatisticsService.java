package com.erdemgural.newssearch.ingestion.internal;

import com.erdemgural.newssearch.ingestion.IngestionStatistics;
import com.erdemgural.newssearch.ingestion.IngestionSummary;
import com.erdemgural.newssearch.ingestion.internal.IngestionStatisticsRepository.FeedCounts;
import java.time.Instant;
import org.springframework.stereotype.Service;

/**
 * {@link IngestionStatistics}'in uygulaması. Sayılar istek anında hesaplanır; panoda gösterilen sayı her zaman
 * günceldir.
 */
@Service
class IngestionStatisticsService implements IngestionStatistics {

    private final IngestionStatisticsRepository repository;

    IngestionStatisticsService(IngestionStatisticsRepository repository) {
        this.repository = repository;
    }

    @Override
    public IngestionSummary summarize(Instant since) {
        FeedCounts feeds = repository.countFeeds();
        return new IngestionSummary(
                repository.countArticlesBySource(since),
                feeds.enabled(),
                feeds.failing(),
                feeds.autoDisabled(),
                repository.findLastRunStartedAt().orElse(null));
    }
}
