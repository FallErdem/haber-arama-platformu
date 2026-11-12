package com.erdemgural.newssearch.identity.internal;

import com.erdemgural.newssearch.identity.CurrentUser;
import com.erdemgural.newssearch.identity.UserRole;
import com.erdemgural.newssearch.identity.UserStatus;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.security.oauth2.server.resource.InvalidBearerTokenException;
import org.springframework.stereotype.Service;
import org.springframework.util.StringUtils;

/**
 * Token'daki kimliği {@code users} tablosundaki kayıtla eşleştirir; kayıt yoksa
 * ilk istekte oluşturur (ADR-0014).
 */
@Service
class UserProvisioningService {

    private final UserRepository userRepository;
    private final IdentityProperties identityProperties;

    UserProvisioningService(UserRepository userRepository, IdentityProperties identityProperties) {
        this.userRepository = userRepository;
        this.identityProperties = identityProperties;
    }

    CurrentUser findOrCreate(Jwt jwt) {
        String keycloakSub = jwt.getSubject();
        return userRepository.findByKeycloakSub(keycloakSub).orElseGet(() -> create(jwt));
    }

    private CurrentUser create(Jwt jwt) {
        String keycloakSub = jwt.getSubject();
        String email = jwt.getClaimAsString("email");
        if (!StringUtils.hasText(email)) {
            // users.email zorunludur; e-postasız bir token ile kayıt oluşturulamaz.
            throw new InvalidBearerTokenException("Token e-posta bilgisi içermiyor");
        }

        boolean isInitialAdmin = isInitialAdmin(jwt, email);
        userRepository.insertIfAbsent(
                keycloakSub,
                email,
                displayNameOf(jwt),
                isInitialAdmin ? UserRole.ADMIN : UserRole.USER,
                isInitialAdmin ? UserStatus.ACTIVE : UserStatus.PENDING);

        return userRepository
                .findByKeycloakSub(keycloakSub)
                .orElseThrow(() -> new IllegalStateException("Kullanıcı kaydı oluşturulamadı"));
    }

    /**
     * Doğrulanmamış bir e-postayla yönetici olunamaması için email_verified şarttır.
     */
    private boolean isInitialAdmin(Jwt jwt, String email) {
        String initialAdminEmail = identityProperties.initialAdminEmail();
        return StringUtils.hasText(initialAdminEmail)
                && Boolean.TRUE.equals(jwt.getClaimAsBoolean("email_verified"))
                && initialAdminEmail.equalsIgnoreCase(email);
    }

    private static String displayNameOf(Jwt jwt) {
        String name = jwt.getClaimAsString("name");
        return StringUtils.hasText(name) ? name : jwt.getClaimAsString("preferred_username");
    }
}
