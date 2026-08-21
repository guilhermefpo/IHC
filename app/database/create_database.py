from app.database.connection import get_connection


def create_database():
    with get_connection() as connection:
        with open("app/database/schema.sql", "r", encoding="utf-8") as file:
            schema = file.read()

        connection.executescript(schema)
        connection.commit()


if __name__ == "__main__":
    create_database()