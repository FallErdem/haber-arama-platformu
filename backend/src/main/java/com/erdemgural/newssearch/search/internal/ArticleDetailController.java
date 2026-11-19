package com.erdemgural.newssearch.search.internal;

import com.erdemgural.newssearch.identity.CurrentUser;
import java.util.UUID;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/articles")
class ArticleDetailController {

    private final ArticleDetailService detailService;

    ArticleDetailController(ArticleDetailService detailService) {
        this.detailService = detailService;
    }

    /** Haber detayı (API sözleşmesi 4.2). Kimlik geçerli bir UUID değilse Spring 400 döner. */
    @GetMapping("/{id}")
    ArticleDetailResponse detail(@AuthenticationPrincipal CurrentUser user, @PathVariable UUID id) {
        return detailService.find(id, user.id());
    }
}
