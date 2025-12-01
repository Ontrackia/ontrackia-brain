from typing import Dict, Any, List, Optional
import sqlite3
import os

from . import config


def _get_conn() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(config.SQLITE_PATH), exist_ok=True)
    conn = sqlite3.connect(config.SQLITE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute(
        """CREATE TABLE IF NOT EXISTS failures (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER,
            aircraft TEXT,
            ata TEXT,
            fault_code TEXT,
            description TEXT,
            corrective_action TEXT,
            failure_type TEXT,
            occurrence_date TEXT,
            reliability_rate REAL
        )"""
    )
    conn.commit()
    conn.close()


def search_failures(company_id: int, filters: Dict[str, Optional[str]]) -> Dict[str, Any]:
    init_db()
    conn = _get_conn()
    cur = conn.cursor()

    where = ["company_id = :company_id"]
    params: Dict[str, Any] = {"company_id": company_id}

    if filters.get("aircraft"):
        where.append("aircraft = :aircraft")
        params["aircraft"] = filters["aircraft"]
    if filters.get("ata"):
        where.append("ata = :ata")
        params["ata"] = filters["ata"]
    if filters.get("fault_code"):
        where.append("fault_code = :fault_code")
        params["fault_code"] = filters["fault_code"]

    sql = "SELECT * FROM failures WHERE " + " AND ".join(where) + " ORDER BY occurrence_date DESC LIMIT 200"
    cur.execute(sql, params)
    rows = cur.fetchall()
    conn.close()

    registros = [dict(r) for r in rows]
    respuesta = (
        f"Found {len(registros)} matching failures in the reliability database. "
        "Use this as context only; always consult OEM and organisational data before decisions."
    )

    return {"respuesta": respuesta, "registros": registros}
