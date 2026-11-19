package com.erdemgural.newssearch.admin.internal;

import com.erdemgural.newssearch.identity.CurrentUser;
import com.erdemgural.newssearch.identity.UserAdministration;
import com.erdemgural.newssearch.identity.UserChange;
import com.erdemgural.newssearch.identity.UserFilter;
import com.erdemgural.newssearch.identity.UserRole;
import com.erdemgural.newssearch.identity.UserStatus;
import com.erdemgural.newssearch.web.FieldError;
import com.erdemgural.newssearch.web.InvalidRequestException;
import com.erdemgural.newssearch.web.PageParameters;
import com.erdemgural.newssearch.web.PageResponse;
import java.util.ArrayList;
import java.util.List;
import java.util.Set;
import java.util.UUID;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

/**
 * Kullanıcı yönetimi (API sözleşmesi 6.1; FG-YP-01 – 03). Yalnızca {@code ADMIN} rolüne açıktır
 * ({@code /api/v1/admin/**}, güvenlik ayarı). Kurallar {@code identity} modülündedir; burada yalnızca
 * istek okunur ve doğrulanır.
 */
@RestController
@RequestMapping("/api/v1/admin/users")
class UserAdminController {

    private static final int MAX_QUERY_LENGTH = 200;

    /** Değişiklik isteğinde verilebilecek durumlar; onay ve ret ayrı uç noktalardır. */
    private static final Set<UserStatus> CHANGEABLE_STATUSES = Set.of(UserStatus.ACTIVE, UserStatus.PASSIVE);

    private final UserAdministration userAdministration;

    UserAdminController(UserAdministration userAdministration) {
        this.userAdministration = userAdministration;
    }

    @GetMapping
    PageResponse<AdminUserResponse> list(
            @RequestParam(required = false) String status,
            @RequestParam(required = false) String role,
            @RequestParam(required = false) String q,
            @RequestParam(required = false) String page,
            @RequestParam(required = false) String size) {
        List<FieldError> errors = new ArrayList<>();
        UserStatus statusFilter = parseEnum("status", status, UserStatus.class, errors);
        UserRole roleFilter = parseEnum("role", role, UserRole.class, errors);
        String query = q == null || q.isBlank() ? null : q.strip();
        if (query != null && query.length() > MAX_QUERY_LENGTH) {
            errors.add(new FieldError("q", FieldError.Code.MAX_LENGTH));
        }
        PageParameters pageParameters = PageParameters.parse(page, size, errors);
        if (!errors.isEmpty()) {
            throw new InvalidRequestException(errors);
        }
        return userAdministration
                .list(new UserFilter(statusFilter, roleFilter, query), pageParameters)
                .map(AdminUserResponse::from);
    }

    @PostMapping("/{id}/approve")
    AdminUserResponse approve(@AuthenticationPrincipal CurrentUser admin, @PathVariable UUID id) {
        return AdminUserResponse.from(userAdministration.approve(admin.id(), id));
    }

    @PostMapping("/{id}/reject")
    AdminUserResponse reject(@AuthenticationPrincipal CurrentUser admin, @PathVariable UUID id) {
        return AdminUserResponse.from(userAdministration.reject(admin.id(), id));
    }

    @PatchMapping("/{id}")
    AdminUserResponse change(
            @AuthenticationPrincipal CurrentUser admin, @PathVariable UUID id, @RequestBody UserChangeRequest body) {
        List<FieldError> errors = new ArrayList<>();
        UserRole role = parseEnum("role", body.role(), UserRole.class, errors);
        UserStatus status = parseEnum("status", body.status(), UserStatus.class, errors);
        if (status != null && !CHANGEABLE_STATUSES.contains(status)) {
            errors.add(new FieldError("status", FieldError.Code.INVALID_VALUE));
        }
        if (body.version() == null) {
            errors.add(new FieldError("version", FieldError.Code.INVALID_VALUE));
        }
        if (!errors.isEmpty()) {
            throw new InvalidRequestException(errors);
        }
        return AdminUserResponse.from(
                userAdministration.change(admin.id(), id, new UserChange(role, status, body.version())));
    }

    /** Boşsa {@code null}; tanınmayan bir değerde hatayı listeye ekler ve {@code null} döner. */
    private static <E extends Enum<E>> E parseEnum(String field, String value, Class<E> type, List<FieldError> errors) {
        if (value == null || value.isBlank()) {
            return null;
        }
        try {
            return Enum.valueOf(type, value.strip());
        } catch (IllegalArgumentException exception) {
            errors.add(new FieldError(field, FieldError.Code.INVALID_VALUE));
            return null;
        }
    }
}
