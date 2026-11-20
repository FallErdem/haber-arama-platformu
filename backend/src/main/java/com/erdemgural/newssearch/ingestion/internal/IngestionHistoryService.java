package com.erdemgural.newssearch.ingestion.internal;

import com.erdemgural.newssearch.ingestion.IngestionHistory;
import com.erdemgural.newssearch.ingestion.IngestionRun;
import com.erdemgural.newssearch.ingestion.IngestionRunFilter;
import com.erdemgural.newssearch.web.PageParameters;
import com.erdemgural.newssearch.web.PageResponse;
import org.springframework.stereotype.Service;

/** {@link IngestionHistory}'nin uygulaması. */
@Service
class IngestionHistoryService implements IngestionHistory {

    private final IngestionRunRepository repository;

    IngestionHistoryService(IngestionRunRepository repository) {
        this.repository = repository;
    }

    @Override
    public PageResponse<IngestionRun> list(IngestionRunFilter filter, PageParameters page) {
        return PageResponse.of(repository.findPage(filter, page.size(), page.offset()), page, repository.count(filter));
    }
}
