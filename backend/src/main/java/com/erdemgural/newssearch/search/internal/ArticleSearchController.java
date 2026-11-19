package com.erdemgural.newssearch.search.internal;

import com.erdemgural.newssearch.identity.CurrentUser;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/articles")
class ArticleSearchController {

    private final ArticleSearchService searchService;

    ArticleSearchController(ArticleSearchService searchService) {
        this.searchService = searchService;
    }

    /**
     * Arama (API sözleşmesi 4.1). Parametreler metin olarak alınır ve {@link SearchCriteria}
     * içinde okunur: böylece sayı olmayan bir {@code page} değeri de diğer doğrulama hataları
     * gibi alan adı ve koduyla bildirilir.
     */
    @GetMapping
    ArticleSearchResponse search(
            @AuthenticationPrincipal CurrentUser user,
            @RequestParam(required = false) String q,
            @RequestParam(required = false) String sources,
            @RequestParam(required = false) String language,
            @RequestParam(required = false) String categories,
            @RequestParam(required = false) String from,
            @RequestParam(required = false) String to,
            @RequestParam(required = false) String sort,
            @RequestParam(required = false) String page,
            @RequestParam(required = false) String size) {
        return searchService.search(
                SearchCriteria.parse(q, sources, language, categories, from, to, sort, page, size), user.id());
    }
}
