from app.database.connection import get_connection


def insert_initial_data():
    departamentos = [
        ("Higiene",),
        ("Bebidas",),
        ("Alimentos",),
        ("Limpeza",),
        ("Eletrônicos",),
        ("Papelaria",),
        ("Hortifruti",),
    ]

    with get_connection() as connection:
        connection.executemany(
            "INSERT OR IGNORE INTO departamentos (nome) VALUES (?)",
            departamentos,
        )

        cursor = connection.execute("SELECT COUNT(*) FROM produtos")
        quantidade_produtos = cursor.fetchone()[0]

        if quantidade_produtos > 0:
            print("Os produtos já foram cadastrados.")
            return

        cursor = connection.execute(
            "SELECT id, nome FROM departamentos"
        )

        departamentos_por_nome = {
            linha["nome"]: linha["id"]
            for linha in cursor.fetchall()
        }

        produtos = [
            (
                "Sabonete",
                "Produto de higiene pessoal",
                12.90,
                300,
                "2025-10-13",
                "2027-09-10",
                1,
                departamentos_por_nome["Higiene"],
            ),
            (
                "Água",
                "Garrafa de água mineral",
                6.50,
                150,
                "2026-05-03",
                "2027-05-03",
                1,
                departamentos_por_nome["Bebidas"],
            ),
            (
                "Arroz",
                "Arroz branco 5 kg",
                29.99,
                200,
                "2026-03-01",
                "2027-03-01",
                1,
                departamentos_por_nome["Alimentos"],
            ),
            (
                "Notebook",
                "Notebook de 15 polegadas",
                3499.90,
                25,
                "2026-01-15",
                "2030-01-15",
                1,
                departamentos_por_nome["Eletrônicos"],
            ),
            (
                "Frango",
                "Peito de frango 1 kg",
                16.90,
                120,
                "2026-08-06",
                "2026-08-21",
                1,
                departamentos_por_nome["Alimentos"],
            ),
        ]

        connection.executemany(
            """
            INSERT INTO produtos (
                nome,
                descricao,
                preco,
                quantidade,
                data_fabricacao,
                data_validade,
                ativo,
                departamento_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            produtos,
        )

        connection.commit()

    print("Dados iniciais inseridos com sucesso.")


if __name__ == "__main__":
    insert_initial_data()