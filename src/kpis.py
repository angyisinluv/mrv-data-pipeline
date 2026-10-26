"""KPI queries on the SQLite database. Survival KPIs use only plots that are not marked needs_review."""
import sqlite3

import pandas as pd


def _query(db_path, sql, params=()):
    with sqlite3.connect(db_path) as conn:
        return pd.read_sql(sql, conn, params=params)


def _where(block):
    """Optional block filter: returns the SQL text and its parameters."""
    if block and block != "All":
        return "WHERE block = ?", (block,)
    return "", ()


def list_blocks(db_path):
    df = _query(db_path, "SELECT DISTINCT block FROM plots ORDER BY block")
    return df["block"].tolist()


def overall_kpis(db_path, block=None):
    where, params = _where(block)
    sql = f"""
        SELECT COUNT(*) AS plots,
               SUM(trees_planted) AS trees_planted,
               SUM(trees_surviving) AS trees_surviving,
               ROUND(100.0 * SUM(trees_surviving) / SUM(trees_planted), 1) AS survival_pct,
               ROUND(SUM(planted_area_ha), 1) AS planted_ha
        FROM usable_plots {where}
    """
    return _query(db_path, sql, params).iloc[0]


def survival_by_block(db_path):
    sql = """
        SELECT block, COUNT(*) AS plots,
               ROUND(100.0 * SUM(trees_surviving) / SUM(trees_planted), 1) AS survival_pct
        FROM usable_plots GROUP BY block ORDER BY block
    """
    return _query(db_path, sql)


def survival_by_irrigation(db_path, block=None):
    where, params = _where(block)
    sql = f"""
        SELECT CASE WHEN irrigation_source IS NULL OR irrigation_source = 'More'
                    THEN 'Unknown' ELSE irrigation_source END AS irrigation_source,
               COUNT(*) AS plots,
               ROUND(100.0 * SUM(trees_surviving) / SUM(trees_planted), 1) AS survival_pct
        FROM usable_plots {where}
        GROUP BY 1 ORDER BY survival_pct DESC
    """
    return _query(db_path, sql, params)


def species_mix(db_path, block=None):
    """Share of surviving trees by species."""
    where, params = _where(block)
    sql = f"""
        SELECT SUM(cashew_surviving) AS Cashew, SUM(mango_surviving) AS Mango,
               SUM(amla_surviving) AS Amla, SUM(neem_surviving) AS Neem
        FROM usable_plots {where}
    """
    row = _query(db_path, sql, params).iloc[0]
    out = row.rename_axis("species").reset_index(name="surviving_trees")
    out["share_pct"] = (100.0 * out["surviving_trees"] / out["surviving_trees"].sum()).round(1)
    return out


def low_survival_plots(db_path, threshold_pct=80, block=None, limit=15):
    where, params = _where(block)
    joiner = "AND" if where else "WHERE"
    sql = f"""
        SELECT farmer_id, block, village, trees_planted, trees_surviving,
               ROUND(100.0 * trees_surviving / trees_planted, 1) AS survival_pct
        FROM usable_plots {where} {joiner} 100.0 * trees_surviving / trees_planted < ?
        ORDER BY survival_pct LIMIT ?
    """
    return _query(db_path, sql, params + (threshold_pct, limit))


def status_counts(db_path, block=None):
    where, params = _where(block)
    sql = f"SELECT status, COUNT(*) AS plots FROM plots {where} GROUP BY status ORDER BY status"
    return _query(db_path, sql, params)


def issues_by_rule(db_path):
    sql = """
        SELECT rule_id, severity, COUNT(*) AS rows_flagged
        FROM issues GROUP BY rule_id, severity ORDER BY rows_flagged DESC
    """
    return _query(db_path, sql)
