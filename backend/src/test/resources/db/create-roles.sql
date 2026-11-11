-- Test veritabanının hazırlığı. Kümede bu rolleri ve veritabanı sahipliğini
-- CloudNativePG oluşturur (deploy/k8s/base/postgres/cluster.yaml); testteki
-- geçici konteynerde aynı durumu bu dosya kurar. Şifreler yalnızca teste aittir.
CREATE ROLE news_owner LOGIN PASSWORD 'test-owner';
CREATE ROLE news_app LOGIN PASSWORD 'test-app';
CREATE ROLE news_worker LOGIN PASSWORD 'test-worker';

ALTER DATABASE news OWNER TO news_owner;
