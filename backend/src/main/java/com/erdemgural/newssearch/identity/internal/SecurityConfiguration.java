package com.erdemgural.newssearch.identity.internal;

import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.HttpMethod;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configurers.AbstractHttpConfigurer;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.web.SecurityFilterChain;

@Configuration(proxyBeanMethods = false)
@EnableConfigurationProperties(IdentityProperties.class)
class SecurityConfiguration {

    @Bean
    SecurityFilterChain apiSecurityFilterChain(
            HttpSecurity http,
            CurrentUserAuthenticationConverter currentUserAuthenticationConverter,
            SecurityExceptionDelegator securityExceptionDelegator)
            throws Exception {
        return http
                // Rol yetkisi yalnızca aktif kullanıcıda bulunur (CurrentUserAuthentication);
                // bu yüzden rol isteyen her kural aynı zamanda "aktif olmalı" demektir.
                .authorizeHttpRequests(requests -> requests
                        // Sağlık kontrolünü Kubernetes yapar ve token'ı yoktur.
                        .requestMatchers("/actuator/health", "/actuator/health/**")
                        .permitAll()
                        // Ölçümleri Prometheus küme içinden okur ve token'ı yoktur. Adres /api altında olmadığı
                        // için dışarıdan erişilemez; kişisel veri içermez, yalnızca sayılar vardır.
                        .requestMatchers("/actuator/prometheus")
                        .permitAll()
                        // Görseller <img> etiketiyle istenir ve etiket token ekleyemez; bu adres token yerine
                        // imzalı ve süreli adres ister (API sözleşmesi 4.4). İmzayı MediaController denetler.
                        .requestMatchers(HttpMethod.GET, "/api/v1/media/*")
                        .permitAll()
                        // Onay bekleyen, pasif veya reddedilmiş kullanıcı da kendi durumunu görebilmeli.
                        .requestMatchers("/api/v1/me")
                        .authenticated()
                        .requestMatchers("/api/v1/admin/**")
                        .hasRole("ADMIN")
                        .anyRequest()
                        .hasAnyRole("USER", "ADMIN"))
                .oauth2ResourceServer(resourceServer -> resourceServer
                        .jwt(jwt -> jwt.jwtAuthenticationConverter(currentUserAuthenticationConverter))
                        .authenticationEntryPoint(securityExceptionDelegator)
                        .accessDeniedHandler(securityExceptionDelegator))
                .exceptionHandling(exceptions -> exceptions
                        .authenticationEntryPoint(securityExceptionDelegator)
                        .accessDeniedHandler(securityExceptionDelegator))
                // Her istek kendi token'ını taşır; sunucuda oturum tutulmaz.
                .sessionManagement(session -> session.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
                // CSRF, tarayıcının kendiliğinden gönderdiği çerezlere karşı bir korumadır;
                // kimlik çerezle değil Authorization başlığıyla taşındığı için gerekmez.
                .csrf(AbstractHttpConfigurer::disable)
                .build();
    }
}
