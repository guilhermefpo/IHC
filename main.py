from fatec import create_db


def main():
    print("Inicializando sistema...")

    try:
        create_db()
        print("Banco de dados inicializado com sucesso.")

    except Exception as e:
        print(f"Erro ao inicializar o banco de dados: {e}")


if __name__ == "__main__":
    main()
