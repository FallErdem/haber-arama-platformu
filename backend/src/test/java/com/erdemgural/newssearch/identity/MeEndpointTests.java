package com.erdemgural.newssearch.identity;

import static org.assertj.core.api.Assertions.assertThat;

import java.time.Instant;
import java.util.Date;
import java.util.List;
import java.util.UUID;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.context.annotation.Import;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.test.web.servlet.assertj.MockMvcTester;
import org.springframework.test.web.servlet.assertj.MvcTestResult;

import com.erdemgural.newssearch.TestDatabaseConfiguration;
import com.erdemgural.newssearch.TestKeycloakConfiguration;
import com.erdemgural.newssearch.TestTokenIssuer;

@SpringBootTest
@AutoConfigureMockMvc
@Import({ TestDatabaseConfiguration.class, TestKeycloakConfiguration.class })
class MeEndpointTests {

	private final MockMvcTester mvc;
	private final TestTokenIssuer tokenIssuer;
	private final JdbcClient jdbcClient;

	@Autowired
	MeEndpointTests(MockMvcTester mvc, TestTokenIssuer tokenIssuer, JdbcClient jdbcClient) {
		this.mvc = mvc;
		this.tokenIssuer = tokenIssuer;
		this.jdbcClient = jdbcClient;
	}

	@Test
	@DisplayName("token olmadan gelen istek 401 ile reddedilir")
	void requestWithoutTokenIsRejected() {
		assertThat(mvc.get().uri("/api/v1/me")).hasStatus(HttpStatus.UNAUTHORIZED);
	}

	@Test
	@DisplayName("süresi dolmuş token 401 ile reddedilir")
	void expiredTokenIsRejected() {
		// Spring Security saat farkı için 60 saniye tolerans tanır; süre bunun ötesinde dolmuş olmalı.
		Instant tenMinutesAgo = Instant.now().minusSeconds(600);
		String token = tokenIssuer.token(claims -> claims
				.issueTime(Date.from(tenMinutesAgo))
				.expirationTime(Date.from(tenMinutesAgo.plusSeconds(300))));

		assertThat(getMe(token)).hasStatus(HttpStatus.UNAUTHORIZED);
	}

	@Test
	@DisplayName("başka bir yayıncının (iss) token'ı 401 ile reddedilir")
	void tokenFromAnotherIssuerIsRejected() {
		String token = tokenIssuer.token(claims -> claims.issuer("http://haber.local/auth/realms/baska"));

		assertThat(getMe(token)).hasStatus(HttpStatus.UNAUTHORIZED);
	}

	@Test
	@DisplayName("hedef kitlesinde (aud) haber-api olmayan token 401 ile reddedilir")
	void tokenForAnotherAudienceIsRejected() {
		String token = tokenIssuer.token(claims -> claims.audience(List.of("account")));

		assertThat(getMe(token)).hasStatus(HttpStatus.UNAUTHORIZED);
	}

	@Test
	@DisplayName("tanınmayan bir anahtarla imzalanmış token 401 ile reddedilir")
	void tokenSignedWithUnknownKeyIsRejected() {
		assertThat(getMe(tokenIssuer.tokenSignedWithUnknownKey())).hasStatus(HttpStatus.UNAUTHORIZED);
	}

	@Test
	@DisplayName("ilk istekte kullanıcı onay bekliyor durumunda ve USER rolüyle oluşturulur")
	void firstRequestCreatesPendingUser() {
		String keycloakSub = UUID.randomUUID().toString();
		String token = tokenIssuer.token(claims -> claims.subject(keycloakSub).claim("email", "yeni@example.test"));

		MvcTestResult result = getMe(token);

		assertThat(result).hasStatusOk();
		assertThat(result).bodyJson().extractingPath("$.email").isEqualTo("yeni@example.test");
		assertThat(result).bodyJson().extractingPath("$.displayName").isEqualTo("Test Kullanıcı");
		assertThat(result).bodyJson().extractingPath("$.role").isEqualTo("USER");
		assertThat(result).bodyJson().extractingPath("$.status").isEqualTo("PENDING");
		assertThat(userCount(keycloakSub)).isEqualTo(1);
	}

	@Test
	@DisplayName("aynı kullanıcının sonraki istekleri yeni kayıt oluşturmaz")
	void laterRequestsReuseTheSameUser() {
		String keycloakSub = UUID.randomUUID().toString();
		String token = tokenIssuer.token(claims -> claims.subject(keycloakSub));

		getMe(token);
		getMe(token);

		assertThat(userCount(keycloakSub)).isEqualTo(1);
	}

	@Test
	@DisplayName("yapılandırılan e-postayla gelen ve e-postası doğrulanmış kullanıcı aktif yönetici olur")
	void verifiedInitialAdminBecomesActiveAdmin() {
		String token = tokenIssuer.token(claims -> claims
				.claim("email", TestKeycloakConfiguration.INITIAL_ADMIN_EMAIL)
				.claim("email_verified", true));

		MvcTestResult result = getMe(token);

		assertThat(result).hasStatusOk();
		assertThat(result).bodyJson().extractingPath("$.role").isEqualTo("ADMIN");
		assertThat(result).bodyJson().extractingPath("$.status").isEqualTo("ACTIVE");
	}

	@Test
	@DisplayName("yönetici e-postası doğrulanmamışsa kullanıcı sıradan bir kullanıcı gibi oluşturulur")
	void unverifiedInitialAdminStaysPendingUser() {
		String token = tokenIssuer.token(claims -> claims
				.claim("email", TestKeycloakConfiguration.INITIAL_ADMIN_EMAIL)
				.claim("email_verified", false));

		MvcTestResult result = getMe(token);

		assertThat(result).hasStatusOk();
		assertThat(result).bodyJson().extractingPath("$.role").isEqualTo("USER");
		assertThat(result).bodyJson().extractingPath("$.status").isEqualTo("PENDING");
	}

	@Test
	@DisplayName("token'da ad yoksa görünen ad olarak kullanıcı adı kullanılır")
	void displayNameFallsBackToUsername() {
		String token = tokenIssuer.token(claims -> claims.claim("name", null));

		assertThat(getMe(token)).bodyJson().extractingPath("$.displayName").isEqualTo("testkullanici");
	}

	private MvcTestResult getMe(String token) {
		return mvc.get().uri("/api/v1/me").header(HttpHeaders.AUTHORIZATION, "Bearer " + token).exchange();
	}

	private Long userCount(String keycloakSub) {
		return jdbcClient.sql("SELECT count(*) FROM users WHERE keycloak_sub = :keycloakSub")
				.param("keycloakSub", keycloakSub)
				.query(Long.class)
				.single();
	}

}
