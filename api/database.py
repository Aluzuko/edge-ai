import pyodbc

CONNECTION_STRING = (
    "Driver={ODBC Driver 17 for SQL Server};"
    "Server=localhost\\SQLEXPRESS;"
    "Database=WildlifeDB;"
    "Trusted_Connection=yes;"
)


class DictCursor:

    def __init__(self, cursor):
        self._cursor = cursor

    def execute(self, sql, params=None):
        if params:
            self._cursor.execute(sql, params)
        else:
            self._cursor.execute(sql)
        return self

    def _row_to_dict(self, row):
        if row is None:
            return None
        columns = [col[0] for col in self._cursor.description]
        return dict(zip(columns, row))

    def fetchone(self):
        return self._row_to_dict(self._cursor.fetchone())

    def fetchall(self):
        return [self._row_to_dict(r) for r in self._cursor.fetchall()]

    @property
    def lastrowid(self):
        self._cursor.execute("SELECT SCOPE_IDENTITY()")
        result = self._cursor.fetchone()
        return int(result[0]) if result and result[0] is not None else None


class DictConnection:
    """Wraps a pyodbc connection to add sqlite3-style conn.execute(...)."""

    def __init__(self, conn):
        self._conn = conn

    def execute(self, sql, params=None):
        cursor = DictCursor(self._conn.cursor())
        return cursor.execute(sql, params)

    def commit(self):
        self._conn.commit()

    def close(self):
        self._conn.close()


def get_db():
    raw_conn = pyodbc.connect(CONNECTION_STRING)
    conn = DictConnection(raw_conn)
    try:
        yield conn
    finally:
        conn.close()