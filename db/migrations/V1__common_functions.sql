-- Satır her güncellendiğinde updated_at alanını şimdiki zamana ayarlar.
-- Alan veritabanında güncellendiğinden API ve işçinin bu alanı ayrıca yazmasına gerek yoktur.
-- Değişikliği kimin yaptığı audit_events tablosunda tutulur (ADR-0016).
CREATE FUNCTION set_updated_at() RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.updated_at := now();
    RETURN NEW;
END;
$$;