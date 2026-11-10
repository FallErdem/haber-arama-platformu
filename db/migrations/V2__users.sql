-- Uygulamanın kullanıcıları ve yetkileri (ADR-0014). Kimlik Keycloak'tan, yetki bu tablodan gelir.
CREATE TABLE users (
    id              uuid        PRIMARY KEY DEFAULT uuidv7(),
    -- Keycloak'taki değişmeyen kullanıcı kimliği; eşleştirme bununla yapılır (R-15).
    keycloak_sub    text        NOT NULL UNIQUE,
    email           text        NOT NULL,
    display_name    text,
    role            text        NOT NULL CHECK (role IN ('USER', 'ADMIN')),
    status          text        NOT NULL CHECK (status IN ('PENDING', 'ACTIVE', 'PASSIVE', 'REJECTED')),
    last_session_id text,
    version         integer     NOT NULL DEFAULT 0,
    created_at      timestamptz NOT NULL DEFAULT now(),
    updated_at      timestamptz NOT NULL DEFAULT now()
);

CREATE TRIGGER users_set_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();