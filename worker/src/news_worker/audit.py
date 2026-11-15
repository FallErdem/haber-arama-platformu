"""Audit log'a sistem kayıtlarının yazılması (ADR-0016).

İşçinin `audit_events` tablosunda yalnızca ekleme yetkisi vardır: kayıt okuyamaz,
değiştiremez ve silemez (V9 betiği). Burada da yalnızca ekleme bulunur.
"""

from collections.abc import Mapping
from uuid import UUID

import psycopg
from psycopg.rows import TupleRow
from psycopg.types.json import Jsonb

# İşlemi bir kullanıcı değil sistem yaptığı için actor_type SYSTEM'dir ve actor_user_id boş kalır.
_INSERT_SYSTEM_EVENT_QUERY = """
    INSERT INTO audit_events (actor_type, action, target_type, target_id, result, details)
    VALUES ('SYSTEM', %(action)s, %(target_type)s, %(target_id)s, 'SUCCESS', %(details)s)
"""


class AuditRepository:
    async def insert_system_event(
        self,
        connection: psycopg.AsyncConnection[TupleRow],
        action: str,
        target_type: str,
        target_id: UUID,
        details: Mapping[str, object],
    ) -> None:
        """Sistemin yaptığı bir işlemi kaydeder.

        `details` yalnızca o işlem için önceden belirlenmiş alanları taşır; şifre, token veya
        API anahtarı gibi gizli bilgi yazılmaz (ADR-0016, 4. bölüm).
        """
        await connection.execute(
            _INSERT_SYSTEM_EVENT_QUERY,
            {
                "action": action,
                "target_type": target_type,
                "target_id": target_id,
                # Jsonb: Python sözlüğünü PostgreSQL'in jsonb türüne çevirir.
                "details": Jsonb(dict(details)),
            },
        )
