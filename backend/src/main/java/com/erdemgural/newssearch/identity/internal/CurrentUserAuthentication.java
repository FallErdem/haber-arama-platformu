package com.erdemgural.newssearch.identity.internal;

import com.erdemgural.newssearch.identity.CurrentUser;
import com.erdemgural.newssearch.identity.UserStatus;
import java.util.List;
import org.springframework.security.authentication.AbstractAuthenticationToken;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.oauth2.jwt.Jwt;

/**
 * Doğrulanmış bir isteğin Spring Security'deki karşılığı: kim olduğu token'dan,
 * ne yapabileceği {@link CurrentUser} kaydından gelir.
 */
class CurrentUserAuthentication extends AbstractAuthenticationToken {

    private final Jwt jwt;
    private final CurrentUser currentUser;

    CurrentUserAuthentication(Jwt jwt, CurrentUser currentUser) {
        super(authoritiesOf(currentUser));
        this.jwt = jwt;
        this.currentUser = currentUser;
        setAuthenticated(true);
    }

    /**
     * Rol yetkisi yalnızca aktif kullanıcıya verilir; onay bekleyen, pasif veya
     * reddedilmiş bir kullanıcı rolü ne olursa olsun yetkisizdir.
     */
    private static List<SimpleGrantedAuthority> authoritiesOf(CurrentUser currentUser) {
        if (currentUser.status() != UserStatus.ACTIVE) {
            return List.of();
        }
        return List.of(new SimpleGrantedAuthority("ROLE_" + currentUser.role().name()));
    }

    @Override
    public CurrentUser getPrincipal() {
        return currentUser;
    }

    @Override
    public Jwt getCredentials() {
        return jwt;
    }
}
