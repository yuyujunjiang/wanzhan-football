from __future__ import annotations

import logging
import time

from app.domain.ledger.pending_settlement import settle_pending_tickets
from app.settings import settings

logger = logging.getLogger(__name__)


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    interval = max(30, settings.settlement_worker_interval_seconds)
    while True:
        try:
            count = settle_pending_tickets()
            logger.info("settled %s pending tickets", count)
        except Exception:
            logger.exception("settlement loop failed")
        time.sleep(interval)


if __name__ == "__main__":
    main()
