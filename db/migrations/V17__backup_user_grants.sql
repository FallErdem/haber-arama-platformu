-- Yedekleme kullanıcısı (05-veri-modeli.md, 7.1). Tabloları okuma yetkisini PostgreSQL'in hazır
-- pg_read_all_data rolünden alır (deploy/k8s/base/postgres/cluster.yaml); burada yalnızca uygulama
-- veritabanına bağlanma izni verilir. V9, bu izni varsayılan olarak herkesten almıştı.
DO $$
BEGIN
    EXECUTE format('GRANT CONNECT ON DATABASE %I TO news_backup', current_database());
END;
$$;
