"""Write the pipeline outputs to a SQLite database."""
import sqlite3


def write_db(db_path, tables):
    """Save each DataFrame as a table and create a view of plots that can be used for reporting."""
    with sqlite3.connect(db_path) as conn:
        for name, frame in tables.items():
            frame.to_sql(name, conn, if_exists="replace", index=False)
        conn.execute("DROP VIEW IF EXISTS usable_plots")
        conn.execute("CREATE VIEW usable_plots AS SELECT * FROM plots WHERE status IN ('clean', 'warning')")
