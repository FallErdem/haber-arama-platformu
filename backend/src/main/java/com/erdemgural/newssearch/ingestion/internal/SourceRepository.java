package com.erdemgural.newssearch.ingestion.internal;

import java.util.List;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Repository;

@Repository
class SourceRepository {

    private final JdbcClient jdbcClient;

    SourceRepository(JdbcClient jdbcClient) {
        this.jdbcClient = jdbcClient;
    }

    /**
     * Arama filtresinde gösterilecek kaynaklar: yalnızca etkin olanlar, adlarına göre sıralı.
     */
    List<SourceResponse> findEnabled() {
        return jdbcClient
                .sql("""
				SELECT code, name, language
				FROM sources
				WHERE enabled
				ORDER BY name
				""")
                .query((row, rowNumber) ->
                        new SourceResponse(row.getString("code"), row.getString("name"), row.getString("language")))
                .list();
    }
}
