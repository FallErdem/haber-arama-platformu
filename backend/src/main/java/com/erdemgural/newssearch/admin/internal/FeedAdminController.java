package com.erdemgural.newssearch.admin.internal;

import com.erdemgural.newssearch.identity.CurrentUser;
import com.erdemgural.newssearch.ingestion.FeedChange;
import com.erdemgural.newssearch.ingestion.ManagedFeed;
import com.erdemgural.newssearch.ingestion.SourceAdministration;
import java.util.Optional;
import java.util.UUID;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import tools.jackson.databind.JsonNode;

/** Besleme düzenleme (API sözleşmesi 6.3; FG-YP-04, FG-YP-07). Yalnızca {@code ADMIN} rolüne açıktır. */
@RestController
@RequestMapping("/api/v1/admin/feeds")
class FeedAdminController {

    /** En seyrek okuma: günde bir. */
    static final int MAX_FETCH_INTERVAL_MINUTES = 1440;

    private final SourceAdministration sourceAdministration;

    FeedAdminController(SourceAdministration sourceAdministration) {
        this.sourceAdministration = sourceAdministration;
    }

    /**
     * Beslemeyi düzenler, etkinleştirir veya devre dışı bırakır. Otomatik kapanmış bir besleme
     * etkinleştirilince art arda hata sayacı sıfırlanır ve besleme hemen okunur (sözleşme 6.3).
     */
    @PatchMapping("/{id}")
    ManagedFeed update(@AuthenticationPrincipal CurrentUser admin, @PathVariable UUID id, @RequestBody JsonNode body) {
        JsonFields fields = new JsonFields(body);
        String name = fields.text("name", SourceAdminController.MAX_NAME_LENGTH);
        String url = fields.text("url", SourceAdminController.MAX_URL_LENGTH);
        fields.requireHttpUrl("url", url);
        Optional<String> defaultCategoryCode = fields.nullableText("defaultCategoryCode", 40);
        Boolean useItemCategories = fields.bool("useItemCategories");
        Integer fetchIntervalMinutes = fields.integer("fetchIntervalMinutes", 1, MAX_FETCH_INTERVAL_MINUTES);
        Boolean enabled = fields.bool("enabled");
        Integer version = fields.requiredInteger("version", 0, Integer.MAX_VALUE);
        fields.throwIfInvalid();

        return sourceAdministration.updateFeed(
                admin.id(),
                id,
                new FeedChange(
                        name, url, defaultCategoryCode, useItemCategories, fetchIntervalMinutes, enabled, version));
    }
}
