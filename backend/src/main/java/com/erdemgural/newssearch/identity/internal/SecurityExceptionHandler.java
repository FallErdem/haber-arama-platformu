package com.erdemgural.newssearch.identity.internal;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.core.Ordered;
import org.springframework.core.annotation.Order;
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

import com.erdemgural.newssearch.web.ApiProblem;
import com.erdemgural.newssearch.web.ErrorCode;

import jakarta.servlet.http.HttpServletRequest;

/**
 * 401 ve 403 yanıtlarını üretir (ADR-0014, API sözleşmesi 2.6).
 */
@RestControllerAdvice
// Genel hata işleyicideki "beklenmeyen hata" kuralından önce değerlendirilmeli.
@Order(Ordered.HIGHEST_PRECEDENCE)
class SecurityExceptionHandler {

	private static final Logger log = LoggerFactory.getLogger(SecurityExceptionHandler.class);

	@ExceptionHandler(AuthenticationException.class)
	ResponseEntity<ProblemDetail> handleUnauthenticated(AuthenticationException exception,
			HttpServletRequest request) {
		log.warn("Kimlik doğrulanamadı: {}", exception.getMessage());
		return ResponseEntity.status(HttpStatus.UNAUTHORIZED)
				.header(HttpHeaders.WWW_AUTHENTICATE, "Bearer")
				.contentType(MediaType.APPLICATION_PROBLEM_JSON)
				.body(ApiProblem.create(HttpStatus.UNAUTHORIZED, ErrorCode.UNAUTHENTICATED, request));
	}

	@ExceptionHandler(AccessDeniedException.class)
	ResponseEntity<ProblemDetail> handleAccessDenied(AccessDeniedException exception, HttpServletRequest request) {
		return ResponseEntity.status(HttpStatus.FORBIDDEN)
				.contentType(MediaType.APPLICATION_PROBLEM_JSON)
				.body(ApiProblem.create(HttpStatus.FORBIDDEN, accessDeniedCode(), request));
	}

	/**
	 * Arayüzün doğru ekranı gösterebilmesi için ret nedeni kullanıcının
	 * durumundan çıkarılır; kullanıcı aktifse neden rolünün yetmemesidir.
	 */
	private static ErrorCode accessDeniedCode() {
		Authentication authentication = SecurityContextHolder.getContext().getAuthentication();
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
