package com.erdemgural.newssearch.web;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.system.CapturedOutput;
import org.springframework.boot.test.system.OutputCaptureExtension;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.context.annotation.Import;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.test.web.servlet.assertj.MockMvcTester;
import org.springframework.test.web.servlet.assertj.MvcTestResult;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

import com.erdemgural.newssearch.TestDatabaseConfiguration;
import com.erdemgural.newssearch.TestKeycloakConfiguration;
import com.erdemgural.newssearch.TestUsers;
import com.erdemgural.newssearch.TestUsers.TestUser;
import com.erdemgural.newssearch.identity.UserRole;
import com.erdemgural.newssearch.identity.UserStatus;

@SpringBootTest
@AutoConfigureMockMvc
@Import({ TestDatabaseConfiguration.class, TestKeycloakConfiguration.class,
		ErrorResponseTests.FailingController.class })
@ExtendWith(OutputCaptureExtension.class)
class ErrorResponseTests {

	private static final String PROBLEM_JSON = "application/problem+json";
	private static final String REQUEST_ID_HEADER = "X-Request-Id";
	private static final String INTERNAL_DETAIL = "gizli-ic-ayrinti";

	/** Yalnızca bu testte bulunan, her çağrıldığında beklenmeyen bir hata fırlatan adres. */
	@RestController
	static class FailingController {

		@GetMapping("/api/v1/test/failure")
		void fail() {
			throw new IllegalStateException(INTERNAL_DETAIL);
		}

	}

	private final MockMvcTester mvc;
	private final TestUsers users;

	@Autowired
	ErrorResponseTests(MockMvcTester mvc, TestUsers users) {
		this.mvc = mvc;
		this.users = users;
	}

	@Test
	@DisplayName("401 yanıtı RFC 9457 biçimindedir ve UNAUTHENTICATED kodunu taşır")
	void unauthenticatedResponseIsProblemDetail() {
		MvcTestResult result = mvc.get().uri("/api/v1/me").exchange();

		assertThat(result).hasStatus(HttpStatus.UNAUTHORIZED);
		assertThat(result.getResponse().getContentType()).startsWith(PROBLEM_JSON);
		// "type" alanı gönderilmez; RFC 9457'ye göre bu "about:blank" ile aynı anlama gelir.
		assertThat(result).bodyJson().doesNotHavePath("$.type");
		assertThat(result).bodyJson().extractingPath("$.title").isEqualTo("Unauthorized");
		assertThat(result).bodyJson().extractingPath("$.status").isEqualTo(401);
		assertThat(result).bodyJson().extractingPath("$.code").isEqualTo("UNAUTHENTICATED");
		assertThat(result).bodyJson().extractingPath("$.instance").isEqualTo("/api/v1/me");
	}

	@Test
	@DisplayName("var olmayan adres 404 ve NOT_FOUND döner")
	void unknownPathIsNotFound() {
		TestUser user = users.create(UserRole.USER, UserStatus.ACTIVE);

		MvcTestResult result = get("/api/v1/yok", user);

		assertThat(result).hasStatus(HttpStatus.NOT_FOUND);
		assertThat(result.getResponse().getContentType()).startsWith(PROBLEM_JSON);
		assertThat(result).bodyJson().extractingPath("$.code").isEqualTo("NOT_FOUND");
	}

	@Test
	@DisplayName("beklenmeyen hata 500 ve INTERNAL_ERROR döner, iç ayrıntı sızdırmaz")
	void unexpectedErrorDoesNotLeakDetails() {
		TestUser user = users.create(UserRole.USER, UserStatus.ACTIVE);

		MvcTestResult result = get("/api/v1/test/failure", user);

		assertThat(result).hasStatus(HttpStatus.INTERNAL_SERVER_ERROR);
		assertThat(result).bodyJson().extractingPath("$.code").isEqualTo("INTERNAL_ERROR");
		assertThat(result).bodyText().doesNotContain(INTERNAL_DETAIL).doesNotContain("IllegalStateException");
	}

	@Test
	@DisplayName("her yanıt, isteğe özgü bir X-Request-Id başlığı taşır")
	void everyResponseHasItsOwnRequestId() {
		TestUser user = users.create(UserRole.USER, UserStatus.ACTIVE);

		String first = get("/api/v1/me", user).getResponse().getHeader(REQUEST_ID_HEADER);
		String second = get("/api/v1/me", user).getResponse().getHeader(REQUEST_ID_HEADER);
		String rejected = mvc.get().uri("/api/v1/me").exchange().getResponse().getHeader(REQUEST_ID_HEADER);

		assertThat(first).isNotBlank();
		assertThat(second).isNotBlank().isNotEqualTo(first);
		assertThat(rejected).isNotBlank();
	}

	@Test
	@DisplayName("istemcinin gönderdiği X-Request-Id kullanılmaz")
	void clientSuppliedRequestIdIsIgnored() {
		MvcTestResult result = mvc.get().uri("/api/v1/me").header(REQUEST_ID_HEADER, "istemci-degeri").exchange();

		assertThat(result.getResponse().getHeader(REQUEST_ID_HEADER)).isNotEqualTo("istemci-degeri");
	}

	@Test
	@DisplayName("log satırları JSON biçimindedir ve istek kimliğini içerir (FOG-39)")
	void logLinesAreJsonAndCarryRequestId(CapturedOutput output) {
		// Token'sız istek 401 alır ve bu durum uygulama loguna yazılır (ADR-0014).
		String requestId = mvc.get().uri("/api/v1/me").exchange().getResponse().getHeader(REQUEST_ID_HEADER);

		assertThat(output.getOut().lines().filter(line -> line.contains(requestId)))
				.isNotEmpty()
				.allSatisfy(line -> assertThat(line).startsWith("{").endsWith("}")
						.contains("\"requestId\":\"" + requestId + "\""));
	}

	private MvcTestResult get(String path, TestUser user) {
		return mvc.get().uri(path).header(HttpHeaders.AUTHORIZATION, "Bearer " + user.token()).exchange();
	}

}
