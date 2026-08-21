CREATE TABLE IF NOT EXISTS departamentos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS produtos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    descricao TEXT,
    preco REAL NOT NULL,
    quantidade INTEGER NOT NULL,
    data_fabricacao TEXT,
    data_validade TEXT,
    ativo INTEGER NOT NULL DEFAULT 1,
    departamento_id INTEGER NOT NULL,

    FOREIGN KEY (departamento_id)
        REFERENCES departamentos(id)
);