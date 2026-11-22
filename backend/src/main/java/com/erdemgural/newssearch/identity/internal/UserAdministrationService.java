package com.erdemgural.newssearch.identity.internal;

import com.erdemgural.newssearch.audit.AuditAction;
import com.erdemgural.newssearch.audit.AuditEvent;
import com.erdemgural.newssearch.audit.AuditLog;
import com.erdemgural.newssearch.audit.AuditTargetType;
import com.erdemgural.newssearch.identity.ManagedUser;
import com.erdemgural.newssearch.identity.UserAdministration;
import com.erdemgural.newssearch.identity.UserChange;
import com.erdemgural.newssearch.identity.UserFilter;
import com.erdemgural.newssearch.identity.UserRole;
import com.erdemgural.newssearch.identity.UserStatus;
import com.erdemgural.newssearch.web.ApiException;
import com.erdemgural.newssearch.web.ErrorCode;
import com.erdemgural.newssearch.web.PageParameters;
import com.erdemgural.newssearch.web.PageResponse;
import java.util.ArrayList;
import java.util.Collection;
import java.util.EnumMap;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.function.Supplier;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.dao.DataAccessException;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.support.TransactionTemplate;

/**
 * {@link UserAdministration}'ın uygulaması: durum geçişleri, iyimser kilitleme, son aktif yönetici
 * kuralı ve audit kayıtları.
 *
 * <p>Her değişiklik ve onun audit kaydı tek veritabanı işleminde yazılır. Bir kural ihlalinde (409) işlem
 * geri alınır; denemenin {@code FAILURE} kaydı bu yüzden işlem bittikten sonra ayrıca yazılır. İşlem bu
 * nedenle {@code @Transactional} yerine {@link TransactionTemplate} ile açılır: hatayı işlemin dışında
 * yakalayabilmek için.
 */
@Service
class UserAdministrationService implements UserAdministration {

    private static final Logger log = LoggerFactory.getLogger(UserAdministrationService.class);

    /** Denenen bir işlem: başarısız olursa hangi kodla ve hangi ayrıntıyla yazılacağı. */
    private record Attempt(AuditAction action, Map<String, Object> details) {}

    private final ManagedUserRepository repository;
    private final AuditLog auditLog;
    private final TransactionTemplate transactionTemplate;

    UserAdministrationService(
            ManagedUserRepository repository, AuditLog auditLog, TransactionTemplate transactionTemplate) {
        this.repository = repository;
        this.auditLog = auditLog;
        this.transactionTemplate = transactionTemplate;
    }

    @Override
    public PageResponse<ManagedUser> list(UserFilter filter, PageParameters page) {
        return PageResponse.of(repository.findPage(filter, page.size(), page.offset()), page, repository.count(filter));
    }

    @Override
    public Map<UUID, String> findEmails(Collection<UUID> userIds) {
        return repository.findEmails(userIds);
    }

    @Override
    public Map<UserStatus, Long> countByStatus() {
        // EnumMap: sıra durumların tanım sırasıdır (onay bekleyen, aktif, pasif, reddedilen).
        Map<UserStatus, Long> counts = new EnumMap<>(UserStatus.class);
        for (UserStatus status : UserStatus.values()) {
            counts.put(status, 0L);
        }
        counts.putAll(repository.countByStatus());
        return counts;
    }

    @Override
    public ManagedUser approve(UUID adminId, UUID userId) {
        return audited(adminId, userId, List.of(new Attempt(AuditAction.USER_APPROVED, Map.of())), () -> {
            requirePending(findForUpdate(userId));
            ManagedUser approved = repository.update(userId, UserRole.USER, UserStatus.ACTIVE);
            recordSuccess(adminId, userId, AuditAction.USER_APPROVED, Map.of());
            return approved;
        });
    }

    @Override
    public ManagedUser reject(UUID adminId, UUID userId) {
        return audited(adminId, userId, List.of(new Attempt(AuditAction.USER_REJECTED, Map.of())), () -> {
            ManagedUser user = requirePending(findForUpdate(userId));
            ManagedUser rejected = repository.update(userId, user.role(), UserStatus.REJECTED);
            recordSuccess(adminId, userId, AuditAction.USER_REJECTED, Map.of());
            return rejected;
        });
    }

    @Override
    public ManagedUser change(UUID adminId, UUID userId, UserChange change) {
        return audited(adminId, userId, attemptsOf(change), () -> {
            repository.lockAdministration();
            ManagedUser user = findForUpdate(userId);
            if (user.version() != change.version()) {
                throw conflict(ErrorCode.VERSION_CONFLICT);
            }
            // Onay bekleyen veya reddedilmiş kullanıcının durumu onay ve ret işlemleriyle değişir.
            if (user.status() != UserStatus.ACTIVE && user.status() != UserStatus.PASSIVE) {
                throw conflict(ErrorCode.INVALID_STATE_TRANSITION);
            }
            UserRole role = change.role() == null ? user.role() : change.role();
            UserStatus status = change.status() == null ? user.status() : change.status();
            if (role == user.role() && status == user.status()) {
                return user;
            }
            boolean staysActiveAdmin = role == UserRole.ADMIN && status == UserStatus.ACTIVE;
            if (user.isActiveAdmin() && !staysActiveAdmin && repository.countActiveAdmins() <= 1) {
                throw conflict(ErrorCode.LAST_ACTIVE_ADMIN);
            }

            ManagedUser updated = repository.update(userId, role, status);
            if (role != user.role()) {
                recordSuccess(adminId, userId, AuditAction.USER_ROLE_CHANGED, fromTo(user.role(), role));
            }
            if (status != user.status()) {
                recordSuccess(adminId, userId, AuditAction.USER_STATUS_CHANGED, fromTo(user.status(), status));
            }
            return updated;
        });
    }

    /**
     * İşi bir veritabanı işleminde çalıştırır. İş bir kural ihlaliyle (409) biterse işlem geri alınmıştır;
     * her denenen işlem için {@code FAILURE} kaydı işlemin dışında yazılır ve hata yine istemciye döner.
     * Kullanıcının bulunamaması (404) bir deneme sayılmaz, yazılmaz.
     */
    private ManagedUser audited(UUID adminId, UUID userId, List<Attempt> attempts, Supplier<ManagedUser> work) {
        try {
            return transactionTemplate.execute(transaction -> work.get());
        } catch (ApiException exception) {
            if (exception.status() == HttpStatus.CONFLICT) {
                recordFailures(adminId, userId, attempts, exception.code());
            }
            throw exception;
        }
    }

    /**
     * Başarısızlık kaydı yazılamazsa (veritabanına ulaşılamıyorsa) istemci yine asıl nedeni (409) görür;
     * kaydın yazılamadığı uygulama loguna düşer.
     */
    private void recordFailures(UUID adminId, UUID userId, List<Attempt> attempts, ErrorCode code) {
        try {
            for (Attempt attempt : attempts) {
                Map<String, Object> details = new HashMap<>(attempt.details());
                details.put("code", code.name());
                auditLog.record(AuditEvent.failure(adminId, attempt.action(), AuditTargetType.USER, userId, details));
            }
        } catch (DataAccessException exception) {
            log.error("Reddedilen kullanıcı yönetimi işleminin audit kaydı yazılamadı", exception);
        }
    }

    /** Değişiklikte istenen her alan ayrı bir işlemdir (FG-AL-01: rol değişikliği, durum değişikliği). */
    private static List<Attempt> attemptsOf(UserChange change) {
        List<Attempt> attempts = new ArrayList<>();
        if (change.role() != null) {
            attempts.add(new Attempt(
                    AuditAction.USER_ROLE_CHANGED, Map.of("to", change.role().name())));
        }
        if (change.status() != null) {
            attempts.add(new Attempt(
                    AuditAction.USER_STATUS_CHANGED,
                    Map.of("to", change.status().name())));
        }
        return attempts;
    }

    private ManagedUser findForUpdate(UUID userId) {
        return repository
                .findForUpdate(userId)
                .orElseThrow(() -> new ApiException(HttpStatus.NOT_FOUND, ErrorCode.NOT_FOUND));
    }

    private static ManagedUser requirePending(ManagedUser user) {
        if (user.status() != UserStatus.PENDING) {
            throw conflict(ErrorCode.INVALID_STATE_TRANSITION);
        }
        return user;
    }

    private void recordSuccess(UUID adminId, UUID userId, AuditAction action, Map<String, Object> details) {
        auditLog.record(AuditEvent.success(adminId, action, AuditTargetType.USER, userId, details));
    }

    private static Map<String, Object> fromTo(Enum<?> from, Enum<?> to) {
        return Map.of("from", from.name(), "to", to.name());
    }

    private static ApiException conflict(ErrorCode code) {
        return new ApiException(HttpStatus.CONFLICT, code);
    }
}
