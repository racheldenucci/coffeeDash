import pandas as pd
import psycopg2
from psycopg2 import Error
from os import environ
from dotenv import load_dotenv

# Carregar variáveis de ambiente do arquivo .env
load_dotenv()

def processar_consumo_interno():
    # Processar dados de consumo interno
    df = pd.read_excel("data/consumoInterno.xlsx", sheet_name="Sheet1", header=0)
    data = []

    # Depuração: Exibir colunas disponíveis
    print("Colunas em consumoInterno.xlsx:", df.columns.tolist())
    print("Primeiras 5 linhas:\n", df.head())

    # Processar apenas a coluna de consumo per capita de café torrado
    for index, row in df.iterrows():
        ano = int(row['Ano'])
        volume = row['Consumo Per Capita Café Torrado (kg / habitante ano)']
        if pd.notna(volume):
            volume = float(volume)  # Manter em kg por habitante/ano
            data.append({
                "ano": ano,
                "volume": volume
            })
            print(f"Processando ano {ano}, volume {volume}")

    print(f"Total de linhas processadas: {len(data)}")
    return pd.DataFrame(data)

def inserir_no_banco(df, table_name, columns, create_table_query):
    conn = None
    cursor = None
    try:
        database_url = environ.get("DB_URL")
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()

        # Criar ou ajustar tabela consumoInterno
        table_name_lower = table_name.lower()
        cursor.execute("SELECT EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = %s)", (table_name_lower,))
        table_exists = cursor.fetchone()[0]
        if not table_exists:
            print(f"Tabela {table_name_lower} não existe, criando...")
            cursor.execute(create_table_query.replace(table_name, table_name_lower))
        else:
            print(f"Tabela {table_name_lower} já existe, truncando dados...")
            cursor.execute(f"TRUNCATE TABLE {table_name_lower} RESTART IDENTITY CASCADE;")

        # Inserir dados
        insert_query = f"INSERT INTO {table_name_lower} ({', '.join(columns)}) VALUES ({', '.join(['%s'] * len(columns))}) ON CONFLICT ON CONSTRAINT {table_name_lower}_pkey DO NOTHING;"
        rows_inserted = 0
        for _, row in df.iterrows():
            values = (int(row['ano']), float(row['volume']))
            cursor.execute(insert_query, values)
            rows_inserted += 1
        conn.commit()
        print(f"Dados inseridos com sucesso em {table_name_lower}! Linhas inseridas: {rows_inserted}")

        cursor.execute(f"SELECT COUNT(*) FROM {table_name_lower};")
        count = cursor.fetchone()[0]
        print(f"Total de linhas na tabela {table_name_lower} após inserção: {count}")
        cursor.execute(f"SELECT * FROM {table_name_lower} ORDER BY ano LIMIT 5;")
        print("Primeiras 5 linhas da tabela consumoInterno:", cursor.fetchall())

    except Error as e:
        print(f"Erro ao inserir no banco em {table_name_lower}: {e.__class__.__name__}: {str(e)}")
        if conn:
            conn.rollback()
            print("Transação revertida. Tentando verificar estado da tabela...")
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table_name_lower};")
                count = cursor.fetchone()[0] if cursor.rowcount >= 0 else 0
                print(f"Linhas na tabela {table_name_lower} após erro: {count}")
            except Error as e2:
                print(f"Falha ao verificar tabela após erro: {e2.__class__.__name__}: {str(e2)}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

if __name__ == "__main__":
    df_consumo_interno = processar_consumo_interno()
    inserir_no_banco(
        df_consumo_interno, "ConsumoInterno", ["ano", "volume"],
        """
        CREATE TABLE ConsumoInterno (
            ano INT PRIMARY KEY,
            volume NUMERIC(12,2)
        );
        """
    )