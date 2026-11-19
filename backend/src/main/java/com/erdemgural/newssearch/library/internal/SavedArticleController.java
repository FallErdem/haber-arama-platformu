package com.erdemgural.newssearch.library.internal;

import com.erdemgural.newssearch.identity.CurrentUser;
import com.erdemgural.newssearch.web.FieldError;
import com.erdemgural.newssearch.web.InvalidRequestException;
import com.erdemgural.newssearch.web.PageParameters;
import com.erdemgural.newssearch.web.PageResponse;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;
import org.springframework.http.HttpStatus;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

/**
 * Kaydedilen haberler (API sözleşmesi 5.1). Kullanıcı adresten değil token'dan gelir: adreste kullanıcı
 * kimliği olmadığı için bir kullanıcının başka birinin kayıtlarına ulaşmasının yolu yoktur.
 */
@RestController
@RequestMapping("/api/v1/me/saved-articles")
class SavedArticleController {

    private final SavedArticleService service;

    SavedArticleController(SavedArticleService service) {
        this.service = service;
    }

    /** Parametreler metin olarak alınır: sayı olmayan bir değer de alan adı ve koduyla bildirilir. */
    @GetMapping
    PageResponse<SavedArticleItem> list(
            @AuthenticationPrincipal CurrentUser user,
            @RequestParam(required = false) String page,
            @RequestParam(required = false) String size) {
        List<FieldError> errors = new ArrayList<>();
        PageParameters pageParameters = PageParameters.parse(page, size, errors);
        if (!errors.isEmpty()) {
            throw new InvalidRequestException(errors);
        }
        return service.list(user.id(), pageParameters);
    }

    /** {@code PUT}: işlem tekrarlanabilir; aynı istek ikinci kez gelirse sonuç değişmez. */
    @PutMapping("/{articleId}")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    void save(@AuthenticationPrincipal CurrentUser user, @PathVariable UUID articleId) {
        service.save(user.id(), articleId);
    }

    @DeleteMapping("/{articleId}")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    void remove(@AuthenticationPrincipal CurrentUser user, @PathVariable UUID articleId) {
        service.remove(user.id(), articleId);
    }
}
