package com.erdemgural.newssearch.admin.internal;

import com.erdemgural.newssearch.identity.CurrentUser;
import com.erdemgural.newssearch.identity.UserAdministration;
import com.erdemgural.newssearch.ingestion.ArticleAdministration;
import com.erdemgural.newssearch.ingestion.ArticleFilter;
import com.erdemgural.newssearch.ingestion.ManagedArticle;
import com.erdemgural.newssearch.search.ArticleModeration;
import com.erdemgural.newssearch.web.FieldError;
import com.erdemgural.newssearch.web.FieldError.Code;
import com.erdemgural.newssearch.web.InvalidRequestException;
import com.erdemgural.newssearch.web.PageParameters;
import com.erdemgural.newssearch.web.PageResponse;
import java.time.Instant;
import java.time.format.DateTimeParseException;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Set;
import java.util.UUID;
import java.util.stream.Collectors;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import tools.jackson.databind.JsonNode;

/**
 * Haber yönetimi: liste, gizleme ve gizlemeyi geri alma (API sözleşmesi 6.6; FG-YP-09). Yalnızca {@code ADMIN}
 * rolüne açıktır ({@code /api/v1/admin/**}, güvenlik ayarı). Gizli haberler aramada bulunmadığından, gizlemeyi
 * geri almak için bu liste kullanılır.
 */
@RestController
@RequestMapping("/api/v1/admin/articles")
class ArticleAdminController {

    static final int MAX_REASON_LENGTH = 500;

    private final ArticleAdministration articleAdministration;
    private final ArticleModeration articleModeration;
    private final UserAdministration userAdministration;

    ArticleAdminController(
            ArticleAdministration articleAdministration,
            ArticleModeration articleModeration,
            UserAdministration userAdministration) {
        this.articleAdministration = articleAdministration;
        this.articleModeration = articleModeration;
        this.userAdministration = userAdministration;
    }

    @GetMapping
    PageResponse<AdminArticleResponse> list(
            @RequestParam(required = false) String hidden,
            @RequestParam(required = false) String sources,
            @RequestParam(required = false) String from,
            @RequestParam(required = false) String to,
            @RequestParam(required = false) String page,
            @RequestParam(required = false) String size) {
        List<FieldError> errors = new ArrayList<>();
        Boolean hiddenFilter = parseBoolean("hidden", hidden, errors);
        Instant fromInstant = parseInstant("from", from, errors);
        Instant toInstant = parseInstant("to", to, errors);
        if (fromInstant != null && toInstant != null && fromInstant.isAfter(toInstant)) {
            errors.add(new FieldError("from", Code.INVALID_RANGE));
        }
        PageParameters pageParameters = PageParameters.parse(page, size, errors);
        if (!errors.isEmpty()) {
            throw new InvalidRequestException(errors);
        }
        PageResponse<ManagedArticle> articles = articleAdministration.list(
                new ArticleFilter(hiddenFilter, splitCodes(sources), fromInstant, toInstant), pageParameters);
        Map<UUID, String> emails = emailsOf(articles.items());
        return articles.map(article -> AdminArticleResponse.from(article, emails));
    }

    /** Gövde: {@code { "reason": "..." }}; gerekçe zorunludur. */
    @PostMapping("/{id}/hide")
    AdminArticleResponse hide(
            @AuthenticationPrincipal CurrentUser admin, @PathVariable UUID id, @RequestBody JsonNode body) {
        JsonFields fields = new JsonFields(body);
        String reason = fields.requiredText("reason", MAX_REASON_LENGTH);
        fields.throwIfInvalid();

        ManagedArticle article = articleModeration.hide(admin.id(), id, reason);
        return AdminArticleResponse.from(article, emailsOf(List.of(article)));
    }

    @PostMapping("/{id}/unhide")
    AdminArticleResponse unhide(@AuthenticationPrincipal CurrentUser admin, @PathVariable UUID id) {
        return AdminArticleResponse.from(articleModeration.unhide(admin.id(), id), Map.of());
    }

    /** Gizleyen yöneticilerin e-postaları, tek sorguyla. */
    private Map<UUID, String> emailsOf(List<ManagedArticle> articles) {
        Set<UUID> adminIds = articles.stream()
                .map(ManagedArticle::hiddenBy)
                .filter(Objects::nonNull)
                .collect(Collectors.toSet());
        return userAdministration.findEmails(adminIds);
    }

    /** Virgülle ayrılmış kodlar: {@code "TRT, NTV"} → {@code [TRT, NTV]}. Tanınmayan kod hiçbir haberle eşleşmez. */
    private static List<String> splitCodes(String value) {
        if (value == null) {
            return List.of();
        }
        return Arrays.stream(value.split(","))
                .map(String::strip)
                .filter(code -> !code.isEmpty())
                .distinct()
                .toList();
    }

    private static Boolean parseBoolean(String field, String value, List<FieldError> errors) {
        if (value == null || value.isBlank()) {
            return null;
        }
        return switch (value.strip()) {
            case "true" -> true;
            case "false" -> false;
            default -> {
                errors.add(new FieldError(field, Code.INVALID_VALUE));
                yield null;
            }
        };
    }

    /** ISO 8601 ve UTC (sözleşme 2.3): {@code 2026-11-05T09:30:00Z}. */
    private static Instant parseInstant(String field, String value, List<FieldError> errors) {
        if (value == null || value.isBlank()) {
            return null;
        }
        try {
            return Instant.parse(value.strip());
        } catch (DateTimeParseException exception) {
            errors.add(new FieldError(field, Code.INVALID_VALUE));
            return null;
        }
    }
}
