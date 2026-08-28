import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(BASE_DIR, "lojas.db")


def create_db():
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS produtos (
            id NUMBER,
            nome TEXT,
            departamento TEXT,
            produto TEXT,
            preco REAL,
            qntd NUMBER,
            data_fabri DATE,
            data_venci DATE,
            status BOOLEAN
        );
    """)

    c.execute("""
        SELECT COUNT(*) FROM produtos
    """)

    count = c.fetchone()[0]

    if count == 0:
        c.execute("""
            INSERT INTO produtos VALUES
            (1, 'sabonete', 'higiene', 'Produto de higiene pessoal', 12.90, 300, '2025-10-13', '2027-09-10', TRUE),
            (2, 'água', 'bebidas', 'Garrafa de água mineral', 67.67, 15, '2026-05-03', '2027-05-03', TRUE),
            (3, 'coca-cola', 'bebidas', 'Refrigerante de cola 2L', 10.40, 700, '2026-06-09', '2027-12-12', TRUE),
            (4, 'notebook', 'eletrônicos', 'Notebook 15 polegadas', 3499.90, 25, '2026-01-15', '2030-01-15', TRUE),
            (5, 'shampoo', 'higiene', 'Shampoo para cabelos', 18.50, 150, '2026-02-10', '2028-02-10', TRUE),
            (6, 'condicionador', 'higiene', 'Condicionador para cabelos', 19.90, 120, '2026-02-12', '2028-02-12', TRUE),
            (7, 'arroz', 'alimentos', 'Arroz branco 5kg', 29.99, 200, '2026-03-01', '2027-03-01', TRUE),
            (8, 'feijão', 'alimentos', 'Feijão carioca 1kg', 8.99, 350, '2026-03-05', '2027-03-05', TRUE),
            (9, 'macarrão', 'alimentos', 'Macarrão espaguete 500g', 5.49, 400, '2026-03-10', '2028-03-10', TRUE),
            (10, 'açúcar', 'alimentos', 'Açúcar refinado 1kg', 4.99, 280, '2026-04-01', '2028-04-01', TRUE),
            (11, 'café', 'alimentos', 'Café torrado e moído 500g', 18.90, 180, '2026-04-05', '2027-10-05', TRUE),
            (12, 'leite', 'bebidas', 'Leite integral 1L', 5.99, 500, '2026-08-01', '2026-09-01', TRUE),
            (13, 'suco', 'bebidas', 'Suco de laranja 1L', 7.50, 220, '2026-07-10', '2027-01-10', TRUE),
            (14, 'bolacha', 'alimentos', 'Biscoito recheado 140g', 3.99, 450, '2026-05-15', '2027-05-15', TRUE),
            (15, 'chocolate', 'alimentos', 'Chocolate ao leite 90g', 6.99, 300, '2026-06-20', '2027-06-20', TRUE),
            (16, 'detergente', 'limpeza', 'Detergente líquido 500ml', 2.99, 600, '2026-01-20', '2028-01-20', TRUE),
            (17, 'sabão', 'limpeza', 'Sabão em pó 1kg', 14.90, 250, '2026-02-15', '2028-02-15', TRUE),
            (18, 'amaciante', 'limpeza', 'Amaciante de roupas 2L', 16.90, 180, '2026-03-20', '2028-03-20', TRUE),
            (19, 'desinfetante', 'limpeza', 'Desinfetante 2L', 9.90, 320, '2026-04-10', '2028-04-10', TRUE),
            (20, 'esponja', 'limpeza', 'Esponja multiuso', 3.50, 700, '2026-05-01', '2030-05-01', TRUE),
            (21, 'papel-higiênico', 'higiene', 'Papel higiênico pacote 12 unidades', 19.99, 250, '2026-01-05', '2030-01-05', TRUE),
            (22, 'creme dental', 'higiene', 'Creme dental 90g', 7.99, 300, '2026-02-01', '2028-02-01', TRUE),
            (23, 'escova dental', 'higiene', 'Escova de dentes', 8.50, 200, '2026-03-01', '2030-03-01', TRUE),
            (24, 'desodorante', 'higiene', 'Desodorante aerosol 150ml', 13.90, 180, '2026-04-15', '2028-04-15', TRUE),
            (25, 'papel-toalha', 'limpeza', 'Papel toalha 2 rolos', 7.90, 230, '2026-05-10', '2030-05-10', TRUE),
            (26, 'celular', 'eletrônicos', 'Smartphone 128GB', 1899.90, 40, '2026-01-10', '2030-01-10', TRUE),
            (27, 'tablet', 'eletrônicos', 'Tablet 10 polegadas', 1299.90, 30, '2026-02-20', '2030-02-20', TRUE),
            (28, 'monitor', 'eletrônicos', 'Monitor LED 24 polegadas', 899.90, 35, '2026-03-15', '2030-03-15', TRUE),
            (29, 'teclado', 'eletrônicos', 'Teclado USB', 89.90, 100, '2026-04-20', '2030-04-20', TRUE),
            (30, 'mouse', 'eletrônicos', 'Mouse óptico USB', 59.90, 150, '2026-05-20', '2030-05-20', TRUE),
            (31, 'fones', 'eletrônicos', 'Fone de ouvido Bluetooth', 149.90, 80, '2026-06-01', '2030-06-01', TRUE),
            (32, 'carregador', 'eletrônicos', 'Carregador USB-C', 79.90, 120, '2026-06-10', '2030-06-10', TRUE),
            (33, 'caderno', 'papelaria', 'Caderno universitário 200 folhas', 24.90, 100, '2026-01-25', '2030-01-25', TRUE),
            (34, 'caneta', 'papelaria', 'Caneta esferográfica azul', 2.50, 500, '2026-02-05', '2030-02-05', TRUE),
            (35, 'lápis', 'papelaria', 'Lápis preto HB', 1.99, 600, '2026-03-05', '2030-03-05', TRUE),
            (36, 'borracha', 'papelaria', 'Borracha branca escolar', 1.50, 450, '2026-04-05', '2030-04-05', TRUE),
            (37, 'mochila', 'papelaria', 'Mochila escolar', 129.90, 60, '2026-05-05', '2030-05-05', TRUE),
            (38, 'carne', 'alimentos', 'Carne bovina 1kg', 39.90, 100, '2026-08-05', '2026-08-20', TRUE),
            (39, 'frango', 'alimentos', 'Peito de frango 1kg', 16.90, 120, '2026-08-06', '2026-08-21', TRUE),
            (40, 'queijo', 'alimentos', 'Queijo muçarela 500g', 24.90, 90, '2026-08-07', '2026-09-07', TRUE),
            (41, 'manteiga', 'alimentos', 'Manteiga 200g', 12.90, 110, '2026-07-15', '2026-10-15', TRUE),
            (42, 'iogurte', 'alimentos', 'Iogurte natural 170g', 4.50, 200, '2026-08-08', '2026-08-25', TRUE),
            (43, 'maçã', 'hortifruti', 'Maçã nacional 1kg', 9.90, 150, '2026-08-10', '2026-08-20', TRUE),
            (44, 'banana', 'hortifruti', 'Banana prata 1kg', 6.90, 180, '2026-08-10', '2026-08-18', TRUE),
            (45, 'laranja', 'hortifruti', 'Laranja 1kg', 5.90, 200, '2026-08-09', '2026-08-19', TRUE),
            (46, 'batata', 'hortifruti', 'Batata inglesa 1kg', 7.90, 170, '2026-08-09', '2026-08-25', TRUE),
            (47, 'tomate', 'hortifruti', 'Tomate 1kg', 8.90, 130, '2026-08-11', '2026-08-18', TRUE),
            (48, 'cebola', 'hortifruti', 'Cebola 1kg', 6.50, 140, '2026-08-11', '2026-08-25', TRUE),
            (49, 'azeite', 'alimentos', 'Azeite de oliva 500ml', 32.90, 75, '2026-01-15', '2028-01-15', TRUE),
            (50, 'farinha', 'alimentos', 'Farinha de trigo 1kg', 5.90, 250, '2026-05-15', '2027-11-15', TRUE)
        """)

    conn.commit()
    conn.close()


if __name__ == "__main__":
    create_db()
