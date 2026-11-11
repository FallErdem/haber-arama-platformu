package com.erdemgural.newssearch.identity;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.context.annotation.Import;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.test.web.servlet.assertj.MockMvcTester;
import org.springframework.test.web.servlet.assertj.MvcTestResult;

import com.erdemgural.newssearch.TestDatabaseConfiguration;
import com.erdemgural.newssearch.TestKeycloakConfiguration;
import com.erdemgural.newssearch.TestUsers;
import com.erdemgural.newssearch.TestUsers.TestUser;

@SpringBootTest
@AutoConfigureMockMvc
@Import({ TestDatabaseConfiguration.class, TestKeycloakConfiguration.class })
class AccessControlTests {

	/** Henüz var olmayan bir adres: aktif kullanıcı 404, yetkisiz kullanıcı 403 alır. */
	private static final String PROTECTED_PATH = "/api/v1/articles";
	private static final String ADMIN_PATH = "/api/v1/admin/users";

	private final MockMvcTester mvc;
	private final TestUsers users;

	@Autowired
	AccessControlTests(MockMvcTester mvc, TestUsers users) {
		this.mvc = mvc;
		this.users = users;
	}

	@Test
	@DisplayName("onay bekleyen kullanıcı 403 ve USER_PENDING_APPROVAL alır")
	void pendingUserIsRejected() {
		TestUser user = users.create(UserRole.USER, UserStatus.PENDING);

		assertRejected(get(PROTECTED_PATH, user), "USER_PENDING_APPROVAL");
	}

	@Test
	@DisplayName("reddedilmiş kullanıcı 403 ve USER_REJECTED alır")
	void rejectedUserIsRejected() {
		TestUser user = users.create(UserRole.USER, UserStatus.REJECTED);

		assertRejected(get(PROTECTED_PATH, user), "USER_REJECTED");
	}

	@Test
	@DisplayName("pasif kullanıcı 403 ve USER_PASSIVE alır")
	void passiveUserIsRejected() {
		TestUser user = users.create(UserRole.USER, UserStatus.PASSIVE);

		assertRejected(get(PROTECTED_PATH, user), "USER_PASSIVE");
	}

	@Test
	@DisplayName("pasif yönetici yönetim adreslerine erişemez")
	void passiveAdminCannotUseAdminEndpoints() {
		TestUser user = users.create(UserRole.ADMIN, UserStatus.PASSIVE);

		assertRejected(get(ADMIN_PATH, user), "USER_PASSIVE");
	}

	@Test
	@DisplayName("aktif ama yönetici olmayan kullanıcı yönetim adreslerinde 403 ve FORBIDDEN alır")
	void activeUserCannotUseAdminEndpoints() {
		TestUser user = users.create(UserRole.USER, UserStatus.ACTIVE);

		assertRejected(get(ADMIN_PATH, user), "FORBIDDEN");
	}

	@Test
	@DisplayName("aktif kullanıcı ve aktif yönetici yetki kontrolünden geçer")
	void activeUsersPassAccessControl() {
		TestUser user = users.create(UserRole.USER, UserStatus.ACTIVE);
		TestUser admin = users.create(UserRole.ADMIN, UserStatus.ACTIVE);

		// Adresler henüz yok; 403 yerine 404 gelmesi yetki kontrolünün geçildiğini gösterir.
		assertThat(get(PROTECTED_PATH, user)).hasStatus(HttpStatus.NOT_FOUND);
		assertThat(get(ADMIN_PATH, admin)).hasStatus(HttpStatus.NOT_FOUND);
	}

	@Test
	@DisplayName("aktif olmayan kullanıcı kendi durumunu /me ile görebilir")
	void inactiveUserCanStillReadOwnStatus() {
		TestUser user = users.create(UserRole.USER, UserStatus.PASSIVE);

		MvcTestResult result = get("/api/v1/me", user);

		assertThat(result).hasStatusOk();
		assertThat(result).bodyJson().extractingPath("$.status").isEqualTo("PASSIVE");
	}

	@Test
	@DisplayName("pasif yapılan kullanıcının erişimi bir sonraki istekte kesilir (FOG-19)")
	void deactivationTakesEffectOnNextRequest() {
		TestUser user = users.create(UserRole.USER, UserStatus.ACTIVE);
		assertThat(get(PROTECTED_PATH, user)).hasStatus(HttpStatus.NOT_FOUND);

		users.changeStatus(user, UserStatus.PASSIVE);

		assertRejected(get(PROTECTED_PATH, user), "USER_PASSIVE");
	}

	@Test
	@DisplayName("sağlık adresleri token istemez, diğer yönetim adresleri kapalıdır")
	void healthEndpointsAreOpenWithoutToken() {
		assertThat(mvc.get().uri("/actuator/health/liveness")).hasStatusOk();
		assertThat(mvc.get().uri("/actuator/health/readiness")).hasStatusOk();
		assertThat(mvc.get().uri("/actuator/env")).hasStatus(HttpStatus.UNAUTHORIZED);
	}

	private MvcTestResult get(String path, TestUser user) {
		return mvc.get().uri(path).header(HttpHeaders.AUTHORIZATION, "Bearer " + user.token()).exchange();
	}

	private static void assertRejected(MvcTestResult result, String expectedCode) {
		assertThat(result).hasStatus(HttpStatus.FORBIDDEN);
		assertThat(result).bodyJson().extractingPath("$.code").isEqualTo(expectedCode);
	}

}
