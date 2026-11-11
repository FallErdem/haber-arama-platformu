package com.erdemgural.newssearch.web.internal;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.HttpStatusCode;
import org.springframework.http.ProblemDetail;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.context.request.WebRequest;
import org.springframework.web.servlet.mvc.method.annotation.ResponseEntityExceptionHandler;

import com.erdemgural.newssearch.web.ApiProblem;
import com.erdemgural.newssearch.web.ErrorCode;

import jakarta.servlet.http.HttpServletRequest;

/**
 * Controller'lardan çıkan hataları tek yerde RFC 9457 yanıtına çevirir.
 * Spring'in kendi hataları (bulunmayan adres, hatalı istek) üst sınıfta
 * karşılanır; burada onlara hata kodu eklenir.
 */
@RestControllerAdvice
class ApiExceptionHandler extends ResponseEntityExceptionHandler {

	private static final Logger log = LoggerFactory.getLogger(ApiExceptionHandler.class);

	@Override
	protected ResponseEntity<Object> handleExceptionInternal(Exception exception, Object body, HttpHeaders headers,
			HttpStatusCode statusCode, WebRequest request) {
		ResponseEntity<Object> response = super.handleExceptionInternal(exception, body, headers, statusCode, request);
		if (response != null && response.getBody() instanceof ProblemDetail problem) {
			// Spring'in ürettiği açıklama iç ayrıntı taşıyabilir; istemciye yalnızca kod gider.
			problem.setDetail(null);
			ErrorCode code = codeFor(statusCode);
			if (code != null) {
				problem.setProperty(ApiProblem.CODE_PROPERTY, code.name());
			}
		}
		return response;
	}

	/**
	 * Beklenmeyen her hata buraya düşer. Ayrıntı yalnızca loga yazılır; istemci
	 * yığın izi, SQL hatası veya sınıf adı görmez.
	 */
	@ExceptionHandler(Exception.class)
	ProblemDetail handleUnexpected(Exception exception, HttpServletRequest request) {
		log.error("Beklenmeyen hata", exception);
		return ApiProblem.create(HttpStatus.INTERNAL_SERVER_ERROR, ErrorCode.INTERNAL_ERROR, request);
	}

	private static ErrorCode codeFor(HttpStatusCode statusCode) {
		if (statusCode.value() == HttpStatus.NOT_FOUND.value()) {
			return ErrorCode.NOT_FOUND;
		}
		if (statusCode.value() == HttpStatus.BAD_REQUEST.value()) {
			return ErrorCode.VALIDATION_FAILED;
		}
		if (statusCode.is5xxServerError()) {
			return ErrorCode.INTERNAL_ERROR;
		}
		return null;
	}

}
