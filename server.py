import sqlite3
import dspy
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(BASE_DIR, "lojas.db")


lm = dspy.LM(
    "openai/litert-community/Qwen3-0.6B",
    api_base="http://localhost:1337/v1",
    api_key="not-needed",
)


dspy.configure(lm=lm)


class TextToSQL(dspy.Signature):
    """Generate SQL from natural language.

    Database schema:
      - produtos: nome, departamento, produto, preco,
        qntd, data_fabri, data_venci, status
    """

    dbschema = dspy.InputField(desc="Database schema")
    question = dspy.InputField(desc="Natural language question")

    sql_query = dspy.OutputField(desc="Valid SQL query")


class ReliableSQLGenerator(dspy.Module):

    def __init__(self):
        super().__init__()

        self.generate_sql = dspy.ChainOfThought(TextToSQL)

    def forward(self, schema, question):

        pred = self.generate_sql(dbschema=schema, question=question)

        return pred


def generate(question):

    schema = """
    CREATE TABLE produtos (
        id NUMBER,
        nome VARCHAR(50),
        departamento VARCHAR(50),
        produto VARCHAR(250),
        preco REAL,
        qntd NUMBER,
        data_fabri DATE,
        data_venci DATE,
        status BOOLEAN
    );
    """

    generator = ReliableSQLGenerator()

    sql = generator.forward(schema, question)

    print("SQL gerado:")
    print(sql.sql_query)

    conn = sqlite3.connect(db_path)

    try:
        results = conn.execute(sql.sql_query).fetchall()

        return results

    finally:
        conn.close()


if __name__ == "__main__":

    question = "qual o departamento do sabonete?"

    result = generate(question)

    print("Resultado:")
    print(result)
