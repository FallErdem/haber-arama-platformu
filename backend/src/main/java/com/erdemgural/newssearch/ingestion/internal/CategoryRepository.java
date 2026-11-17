package com.erdemgural.newssearch.ingestion.internal;

import com.erdemgural.newssearch.ingestion.CategoryCatalog;
import java.time.Duration;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Repository;

@Repository
class CategoryRepository implements CategoryCatalog {

    private final JdbcClient jdbcClient;

    CategoryRepository(JdbcClient jdbcClient) {
        this.jdbcClient = jdbcClient;
    }

    /** Bütün kategoriler, arayüzde gösterilecekleri sırayla ({@code sort_order}). */
    List<CategoryResponse> findAll() {
        return jdbcClient
                .sql("""
				SELECT code, kind, sort_order
				FROM categories
				ORDER BY sort_order
				""")
                .query((row, rowNumber) ->
                        new CategoryResponse(row.getString("code"), row.getString("kind"), row.getInt("sort_order")))
                .list();
    }

    /** Süresi tanımlı kategoriler ({@code window_hours} dolu olanlar); başlangıç verisinde yalnızca Son Dakika. */
    @Override
    public Map<String, Duration> timeWindows() {
        return jdbcClient
                .sql("""
				SELECT code, window_hours
				FROM categories
				WHERE window_hours IS NOT NULL
				""")
                .query((row, rowNumber) ->
                        Map.entry(row.getString("code"), Duration.ofHours(row.getInt("window_hours"))))
                .list()
                .stream()
                .collect(Collectors.toMap(Map.Entry::getKey, Map.Entry::getValue));
    }
}
