package com.erdemgural.newssearch.identity.internal;

import java.util.UUID;

import com.erdemgural.newssearch.identity.CurrentUser;
import com.erdemgural.newssearch.identity.UserRole;
import com.erdemgural.newssearch.identity.UserStatus;

/**
 * {@code GET /api/v1/me} yanıtı (API sözleşmesi, 3. bölüm).
 */
record MeResponse(UUID id, String email, String displayName, UserRole role, UserStatus status) {

	static MeResponse from(CurrentUser currentUser) {
		return new MeResponse(
				currentUser.id(),
				currentUser.email(),
				currentUser.displayName(),
				currentUser.role(),
				currentUser.status());
	}

}
