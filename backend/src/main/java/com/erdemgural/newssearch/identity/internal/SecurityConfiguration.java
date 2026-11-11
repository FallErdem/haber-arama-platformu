package com.erdemgural.newssearch.identity.internal;

import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configurers.AbstractHttpConfigurer;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.web.SecurityFilterChain;

@Configuration(proxyBeanMethods = false)
@EnableConfigurationProperties(IdentityProperties.class)
class SecurityConfiguration {

	@Bean
	SecurityFilterChain apiSecurityFilterChain(HttpSecurity http,
			CurrentUserAuthenticationConverter currentUserAuthenticationConverter) throws Exception {
		return http
				.authorizeHttpRequests(requests -> requests.anyRequest().authenticated())
				.oauth2ResourceServer(resourceServer -> resourceServer
						.jwt(jwt -> jwt.jwtAuthenticationConverter(currentUserAuthenticationConverter)))
				// Her istek kendi token'ını taşır; sunucuda oturum tutulmaz.
				.sessionManagement(session -> session.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
				// CSRF, tarayıcının kendiliğinden gönderdiği çerezlere karşı bir korumadır;
				// kimlik çerezle değil Authorization başlığıyla taşındığı için gerekmez.
				.csrf(AbstractHttpConfigurer::disable)
				.build();
	}

}
