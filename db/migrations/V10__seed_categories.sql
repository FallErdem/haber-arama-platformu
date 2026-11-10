-- Ortak kategori listesi (ADR-0004; 05-veri-modeli.md, 3.4).
-- Sıra numaraları onar onar artar; araya yeni bir kategori eklenebilir.
INSERT INTO categories (code, kind, sort_order, window_hours) VALUES
    ('GENERAL',      'TOPIC',    10, NULL),
    ('WORLD',        'TOPIC',    20, NULL),
    ('ECONOMY',      'TOPIC',    30, NULL),
    ('SPORTS',       'TOPIC',    40, NULL),
    ('HEALTH',       'TOPIC',    50, NULL),
    ('SCIENCE_TECH', 'TOPIC',    60, NULL),
    ('CULTURE_ARTS', 'TOPIC',    70, NULL),
    ('LIFESTYLE',    'TOPIC',    80, NULL),
    ('BREAKING',     'TEMPORAL', 90, 6),
    ('OTHER',        'TOPIC',    100, NULL);