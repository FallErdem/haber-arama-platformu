package com.erdemgural.newssearch.identity.internal;

import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import com.erdemgural.newssearch.identity.CurrentUser;

@RestController
@RequestMapping("/api/v1/me")
class MeController {

	/**
	 * Durumu aktif olmayan kullanıcılara da açıktır; arayüz hangi ekranı
	 * göstereceğine bu yanıta göre karar verir.
	 */
	@GetMapping
	MeResponse me(@AuthenticationPrincipal CurrentUser currentUser) {
		return MeResponse.from(currentUser);
	}

}
