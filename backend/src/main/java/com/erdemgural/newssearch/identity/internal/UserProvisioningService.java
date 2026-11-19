package com.erdemgural.newssearch.identity.internal;

import com.erdemgural.newssearch.audit.AuditAction;
import com.erdemgural.newssearch.audit.AuditEvent;
import com.erdemgural.newssearch.audit.AuditLog;
import com.erdemgural.newssearch.audit.AuditTargetType;
import com.erdemgural.newssearch.identity.CurrentUser;
import com.erdemgural.newssearch.identity.UserRole;
import com.erdemgural.newssearch.identity.UserStatus;
import com.erdemgural.newssearch.identity.internal.UserRepository.StoredUser;
import java.util.Map;
import java.util.UUID;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.security.oauth2.server.resource.InvalidBearerTokenException;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.StringUtils;

/**
 * Token'daki kimliği {@code users} tablosundaki kayıtla eşleştirir; kayıt yoksa
 * ilk istekte oluşturur (ADR-0014). Kullanıcı kaydının oluşturulmasını ve yeni
 * oturumu audit log'a yazar (ADR-0016, FG-AL-01).
 */
@Service
class UserProvisioningService {

    private final UserRepository userRepository;
    private final IdentityProperties identityProperties;
    private final AuditLog auditLog;

    UserProvisioningService(UserRepository userRepository, IdentityProperties identityProperties, AuditLog auditLog) {
        this.userRepository = userRepository;
        this.identityProperties = identityProperties;
        this.auditLog = auditLog;
    }

    /**
     * Tek veritabanı işlemi: kullanıcı kaydı ve oturum kimliği ile bunların audit kayıtları birlikte
     * kalıcı olur ya da hiçbiri olmaz (ADR-0016 5. bölüm).
     */
    @Transactional
    CurrentUser findOrCreate(Jwt jwt) {
        StoredUser stored = userRepository.findByKeycloakSub(jwt.getSubject()).orElseGet(() -> create(jwt));
        recordSessionIfNew(stored, jwt);
        return stored.user();
    }

    private StoredUser create(Jwt jwt) {
        String keycloakSub = jwt.getSubject();
        String email = jwt.getClaimAsString("email");
        if (!StringUtils.hasText(email)) {
            // users.email zorunludur; e-postasız bir token ile kayıt oluşturulamaz.
            throw new InvalidBearerTokenException("Token e-posta bilgisi içermiyor");
        }

        boolean isInitialAdmin = isInitialAdmin(jwt, email);
        UserRole role = isInitialAdmin ? UserRole.ADMIN : UserRole.USER;
        UserStatus status = isInitialAdmin ? UserStatus.ACTIVE : UserStatus.PENDING;
        boolean inserted = userRepository.insertIfAbsent(keycloakSub, email, displayNameOf(jwt), role, status);

        StoredUser stored = userRepository
                .findByKeycloakSub(keycloakSub)
                .orElseThrow(() -> new IllegalStateException("Kullanıcı kaydı oluşturulamadı"));
        // Aynı anda gelen ilk iki istekten kaydı yalnızca ekleyen istek yazar; kayıt bir kez oluşur.
        if (inserted) {
            UUID userId = stored.user().id();
            auditLog.record(AuditEvent.success(
                    userId,
                    AuditAction.USER_REGISTERED,
                    AuditTargetType.USER,
                    userId,
                    Map.of("role", role.name(), "status", status.name())));
        }
        return stored;
    }

    /**
     * Token'daki oturum kimliği ({@code sid}) kullanıcının son oturumundan farklıysa yeni bir oturum
     * açılmıştır. Uygulama Keycloak'taki girişi görmez, yalnızca sonrasındaki istekleri görür; yeni oturum
     * buradan anlaşılır (ADR-0016 1. bölüm). Kimlik aynıysa veritabanına yazılmaz: her istekte fazladan bir
     * güncelleme olmaz. Oturum kimliğinin kendisi audit kaydına yazılmaz.
     */
    private void recordSessionIfNew(StoredUser stored, Jwt jwt) {
        String sessionId = jwt.getClaimAsString("sid");
        if (!StringUtils.hasText(sessionId) || sessionId.equals(stored.lastSessionId())) {
            return;
        }
        UUID userId = stored.user().id();
        if (userRepository.startSession(userId, sessionId)) {
            auditLog.record(
                    AuditEvent.success(userId, AuditAction.SESSION_STARTED, AuditTargetType.USER, userId, Map.of()));
        }
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
