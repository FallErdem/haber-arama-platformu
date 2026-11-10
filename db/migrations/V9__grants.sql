-- Uygulama kullanıcılarının yetkileri (05-veri-modeli.md, 7.1).
-- Tabloların sahibi news_owner'dır. Yeni bir tablo ekleyen her geçiş betiği,
-- o tablonun yetkilerini de kendisi vermelidir.

-- Uygulama veritabanına yalnızca uygulama kullanıcıları bağlanabilir.
-- PostgreSQL varsayılan olarak her kullanıcının her veritabanına bağlanmasına izin verir.
DO $$
BEGIN
    EXECUTE format('REVOKE CONNECT ON DATABASE %I FROM PUBLIC', current_database());
    EXECUTE format('GRANT CONNECT ON DATABASE %I TO news_app, news_worker', current_database());
END;
$$;

-- Spring Boot API: bütün tablolarda okuma ve yazma; audit kayıtlarında yalnızca okuma ve ekleme.
GRANT SELECT, INSERT, UPDATE, DELETE ON
    users, sources, feeds, categories, category_mappings,
    articles, article_categories, media,
    ingestion_runs, feed_tests, outbox_events,
    saved_articles, saved_searches
TO news_app;

GRANT SELECT, INSERT ON audit_events TO news_app;

-- Python işçisi: yalnızca yaptığı işlerin gerektirdiği tablolar ve işlemler (ADR-0017).
-- Kullanıcı tablolarına (users, saved_articles, saved_searches) erişimi yoktur.
GRANT SELECT, UPDATE ON sources, feeds TO news_worker;
GRANT SELECT ON categories, category_mappings TO news_worker;
GRANT SELECT, INSERT, UPDATE, DELETE ON articles, media, ingestion_runs, outbox_events TO news_worker;
GRANT SELECT, INSERT, DELETE ON article_categories TO news_worker;
-- Testleri yönetici oluşturur; işçi yalnızca sonucunu yazar ve eskilerini siler.
GRANT SELECT, UPDATE, DELETE ON feed_tests TO news_worker;
-- Sistem kaynaklı audit kayıtları için yalnızca ekleme.
GRANT INSERT ON audit_events TO news_worker;