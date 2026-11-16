"""Logları yapılandırılmış (JSON) biçimde yazar; her satır tek bir JSON nesnesidir."""

import json
import logging
import sys
from datetime import UTC, datetime

SERVICE_NAME = "news-worker"


class JsonFormatter(logging.Formatter):
    """Alan adları, API'nin loglarındaki gibi Elastic Common Schema'yı izler."""

    def format(self, record: logging.LogRecord) -> str:
        entry: dict[str, str] = {
            "@timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "log.level": record.levelname,
            "log.logger": record.name,
            "service.name": SERVICE_NAME,
            "message": record.getMessage(),
        }
        if record.exc_info:
            entry["error.stack_trace"] = self.formatException(record.exc_info)
        # ensure_ascii=False: Türkçe karakterler \u kaçışlarıyla değil olduğu gibi yazılır.
        return json.dumps(entry, ensure_ascii=False)


def configure_logging() -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(logging.INFO)
    # httpx her isteği adresiyle birlikte INFO düzeyinde loglar. Aynı bilgi toplama akışının kendi
    # satırlarında vardır; ayrıca adresinde API anahtarı taşıyan kaynaklarda (NYT) anahtar loga
    # maskelenmeden yazılırdı (R-18). Bu yüzden httpx'in yalnızca uyarı ve hataları yazılır.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    # Elasticsearch istemcisi her isteği INFO düzeyinde, başarısız her bağlantı denemesini de
    # WARNING düzeyinde yığın iziyle loglar. İkisinin bilgisi de outbox aktarımının kendi
    # satırlarında vardır ("Outbox aktarıldı", "Elasticsearch'e ulaşılamadı"); Elasticsearch
    # kapalıyken logun yığın izleriyle dolmaması için istemcinin yalnızca hataları yazılır.
    logging.getLogger("elastic_transport").setLevel(logging.ERROR)
