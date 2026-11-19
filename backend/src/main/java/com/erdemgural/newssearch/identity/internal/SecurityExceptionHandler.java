package com.erdemgural.newssearch.identity.internal;

import com.erdemgural.newssearch.audit.AuditAction;
import com.erdemgural.newssearch.audit.AuditEvent;
import com.erdemgural.newssearch.audit.AuditLog;
import com.erdemgural.newssearch.identity.CurrentUser;
import com.erdemgural.newssearch.web.ApiProblem;
import com.erdemgural.newssearch.web.ErrorCode;
import jakarta.servlet.http.HttpServletRequest;
import java.util.Map;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.core.Ordered;
import org.springframework.core.annotation.Order;
import org.springframework.dao.DataAccessException;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ProblemDetail;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.AccessDeniedException;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.AuthenticationException;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

/**
 * 401 ve 403 yanıtlarını üretir (ADR-0014, API sözleşmesi 2.6). Kimliği doğrulanmış kullanıcının
 * reddedilen istekleri (403) audit log'a, kimliği doğrulanamayan istekler (401) yalnızca uygulama
 * loguna yazılır: sahibi bilinmeyen isteklerle silinemeyen audit tablosu doldurulamasın (ADR-0016).
 */
@RestControllerAdvice
// Genel hata işleyicideki "beklenmeyen hata" kuralından önce değerlendirilmeli.
@Order(Ordered.HIGHEST_PRECEDENCE)
class SecurityExceptionHandler {

    private static final Logger log = LoggerFactory.getLogger(SecurityExceptionHandler.class);

    private final AuditLog auditLog;

    SecurityExceptionHandler(AuditLog auditLog) {
        this.auditLog = auditLog;
    }

    @ExceptionHandler(AuthenticationException.class)
    ResponseEntity<ProblemDetail> handleUnauthenticated(AuthenticationException exception, HttpServletRequest request) {
        log.warn("Kimlik doğrulanamadı: {}", exception.getMessage());
        return ResponseEntity.status(HttpStatus.UNAUTHORIZED)
                .header(HttpHeaders.WWW_AUTHENTICATE, "Bearer")
                .contentType(MediaType.APPLICATION_PROBLEM_JSON)
                .body(ApiProblem.create(HttpStatus.UNAUTHORIZED, ErrorCode.UNAUTHENTICATED, request));
    }

    @ExceptionHandler(AccessDeniedException.class)
    ResponseEntity<ProblemDetail> handleAccessDenied(AccessDeniedException exception, HttpServletRequest request) {
        Authentication authentication = SecurityContextHolder.getContext().getAuthentication();
        ErrorCode code = accessDeniedCode(authentication);
        if (authentication instanceof CurrentUserAuthentication currentUserAuthentication) {
            recordAccessDenied(currentUserAuthentication.getPrincipal(), code, request);
        }
        return ResponseEntity.status(HttpStatus.FORBIDDEN)
                .contentType(MediaType.APPLICATION_PROBLEM_JSON)
                .body(ApiProblem.create(HttpStatus.FORBIDDEN, code, request));
    }

    /**
     * Reddedilen isteğin kaydı. Ayrıntıda yalnızca yöntem, adres yolu ve ret nedeni bulunur. Sorgu metni
     * ({@code ?q=...}) yazılmaz: arama ifadeleri kişiye bağlı olarak kaydedilmemelidir (FG-AL-05).
     *
     * <p>Bir iş işlemine bağlı değildir, kendi başına yazılır (ADR-0016 5. bölüm). Veritabanına
     * ulaşılamazsa kullanıcı yine 403 alır; kaydın yazılamadığı uygulama loguna düşer.
     */
    private void recordAccessDenied(CurrentUser user, ErrorCode code, HttpServletRequest request) {
        try {
            auditLog.record(AuditEvent.failure(
                    user.id(),
                    AuditAction.ACCESS_DENIED,
                    Map.of("method", request.getMethod(), "path", request.getRequestURI(), "code", code.name())));
        } catch (DataAccessException exception) {
            log.error("Reddedilen isteğin audit kaydı yazılamadı", exception);
        }
    }

    /**
     * Arayüzün doğru ekranı gösterebilmesi için ret nedeni kullanıcının
     * durumundan çıkarılır; kullanıcı aktifse neden rolünün yetmemesidir.
     */
    private static ErrorCode accessDeniedCode(Authentication authentication) {
        if (!(authentication instanceof CurrentUserAuthentication currentUserAuthentication)) {
            return ErrorCode.FORBIDDEN;
        }
        return switch (currentUserAuthentication.getPrincipal().status()) {
            case PENDING -> ErrorCode.USER_PENDING_APPROVAL;
            case REJECTED -> ErrorCode.USER_REJECTED;
            case PASSIVE -> ErrorCode.USER_PASSIVE;
            case ACTIVE -> ErrorCode.FORBIDDEN;
        };
    }
}
