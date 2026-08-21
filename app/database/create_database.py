from pathlib import Path

from app.database.connection import get_connection

SCHEMA_PATH = Path(__file__).with_name("schema.sql")


def create_database():
    with open(SCHEMA_PATH, "r", encoding="utf-8") as arquivo:
        schema = arquivo.read()

    with get_connection() as connection:
        connection.executescript(schema)
        connection.commit()

    print("Banco e tabelas criados com sucesso.")


if __name__ == "__main__":
    create_database()