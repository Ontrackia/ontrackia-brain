from typing import Dict, Any
import sqlite3
import os
from . import config


def _get_conn() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(config.SQLITE_PATH), exist_ok=True)
    conn = sqlite3.connect(config.SQLITE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def compute_trends(company_id: int) -> Dict[str, Any]:
    conn = _get_conn()
    cur = conn.cursor()

    # Simple stats by ATA and aircraft
    cur.execute("SELECT ata, COUNT(*) as count FROM failures WHERE company_id = ? GROUP BY ata", (company_id,))
    by_ata = [dict(r) for r in cur.fetchall()]

    cur.execute("SELECT aircraft, COUNT(*) as count FROM failures WHERE company_id = ? GROUP BY aircraft", (company_id,))
    by_aircraft = [dict(r) for r in cur.fetchall()]

    conn.close()

    return {
        "by_ata": by_ata,
        "by_aircraft": by_aircraft,
    }
