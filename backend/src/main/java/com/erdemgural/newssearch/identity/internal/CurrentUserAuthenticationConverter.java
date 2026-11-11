package com.erdemgural.newssearch.identity.internal;

import org.springframework.core.convert.converter.Converter;
import org.springframework.security.authentication.AbstractAuthenticationToken;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.stereotype.Component;

/**
 * Spring Security token'ı doğruladıktan sonra çağrılır; token'ın sahibini
 * {@code users} tablosundaki kullanıcıya çevirir. Her istekte çalıştığı için
 * rol ve durum değişiklikleri bir sonraki istekte geçerli olur (ADR-0014).
 */
@Component
class CurrentUserAuthenticationConverter implements Converter<Jwt, AbstractAuthenticationToken> {

	private final UserProvisioningService userProvisioningService;

	CurrentUserAuthenticationConverter(UserProvisioningService userProvisioningService) {
		this.userProvisioningService = userProvisioningService;
	}

	@Override
	public AbstractAuthenticationToken convert(Jwt jwt) {
		return new CurrentUserAuthentication(jwt, userProvisioningService.findOrCreate(jwt));
	}

}
