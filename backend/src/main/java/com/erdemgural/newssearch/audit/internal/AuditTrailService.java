package com.erdemgural.newssearch.audit.internal;

import com.erdemgural.newssearch.audit.AuditEventFilter;
import com.erdemgural.newssearch.audit.AuditRecord;
import com.erdemgural.newssearch.audit.AuditTrail;
import com.erdemgural.newssearch.web.PageParameters;
import com.erdemgural.newssearch.web.PageResponse;
import java.util.List;
import java.util.function.Consumer;
import org.springframework.stereotype.Service;

/** {@link AuditTrail}'in uygulaması. */
@Service
class AuditTrailService implements AuditTrail {

    /** Dışa aktarmada bir seferde okunan kayıt sayısı: belleği sınırlı tutar, sorgu sayısını da az. */
    static final int CHUNK_SIZE = 1_000;

    private final AuditEventRepository repository;

    AuditTrailService(AuditEventRepository repository) {
        this.repository = repository;
    }

    @Override
    public PageResponse<AuditRecord> list(AuditEventFilter filter, PageParameters page) {
        return PageResponse.of(repository.findPage(filter, page.size(), page.offset()), page, repository.count(filter));
    }

    @Override
    public long count(AuditEventFilter filter) {
        return repository.count(filter);
    }

    @Override
    public void forEachChunk(AuditEventFilter filter, Consumer<List<AuditRecord>> consumer) {
        AuditRecord last = null;
        while (true) {
            List<AuditRecord> chunk = repository.findChunkAfter(filter, last, CHUNK_SIZE);
            if (chunk.isEmpty()) {
                return;
            }
            consumer.accept(chunk);
            // Parça dolu değilse sonraki sorgu boş dönerdi; boşuna sorulmaz.
            if (chunk.size() < CHUNK_SIZE) {
                return;
            }
            last = chunk.getLast();
        }
    }
}
