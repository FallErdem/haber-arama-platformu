package com.erdemgural.newssearch.web;

import java.net.URI;

import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;

import jakarta.servlet.http.HttpServletRequest;

/**
 * API'nin bütün hata yanıtlarını aynı biçimde üretir (RFC 9457, API sözleşmesi 2.6).
 */
public final class ApiProblem {

	/** Hata kodunun yanıt gövdesindeki alan adı. */
	public static final String CODE_PROPERTY = "code";

	private ApiProblem() {
	}

	public static ProblemDetail create(HttpStatus status, ErrorCode code, HttpServletRequest request) {
		ProblemDetail problem = ProblemDetail.forStatus(status);
		problem.setTitle(status.getReasonPhrase());
		problem.setInstance(URI.create(request.getRequestURI()));
		problem.setProperty(CODE_PROPERTY, code.name());
		return problem;
	}

}
