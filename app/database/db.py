import psycopg2
from psycopg2.extras import RealDictCursor
from app.config import DB_CONFIG


def get_connection():
    return psycopg2.connect(
        **DB_CONFIG,
        cursor_factory=RealDictCursor
    )