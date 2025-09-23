import pandas as pd
import psycopg2
from psycopg2 import Error
from os import environ
from dotenv import load_dotenv

# Carregar variáveis de ambiente do arquivo .env
load_dotenv()

def processar_exportacao():
    # Processar dados de exportação
    df_volume = pd.read_excel("data/exportacoes.xlsx", sheet_name="VOLUME (SACAS)", usecols="A:G", header=1)
    df_receita = pd.read_excel("data/exportacoes.xlsx", sheet_name="RECEITA CAMBIAL (US$ MIL)", usecols="A:G", header=1)
    data = []

    # Depuração: Exibir colunas disponíveis
    print("Colunas em VOLUME (SACAS):", df_volume.columns.tolist())
    print("Colunas em RECEITA CAMBIAL (US$ MIL):", df_receita.columns.tolist())
    print("Primeiras 5 linhas de VOLUME (SACAS):\n", df_volume.head())

    # Mapear espécies e tipos
    especie_map = {'Conillon': 3, 'Robusta': 2, 'Arábica': 1} 
    tipo_map = {'Verde': 1, 'Torrado': 2, 'Solúvel': 3}

    # Processar dados anuais
    for index, row in df_volume.iterrows():
        ano = int(row['Mês/Ano'].replace('Ano ', ''))
        for col, especie in [('Conillon', 3), ('Arábica', 1)]:
            volume = row[col]
            if pd.notna(volume):
                for tipo_col, tipo in [('Verde', 1), ('Torrado', 2), ('Solúvel', 3)]:
                    receita_col = tipo_col  # Mesma ordem na planilha de receita
                    receita = df_receita.iloc[index][col] if pd.notna(df_receita.iloc[index][col]) else 0
                    if pd.notna(volume):
                        data.append({
                            "ano": ano,
                            "idTipo": tipo,
                            "idEspecie": especie,
                            "receita": float(receita) * 1000,  # Converter de mil para unidades
                            "volume": float(volume)
                        })
                        print(f"Processando ano {ano}, espécie {col}, tipo {tipo_col}, volume {volume}, receita {receita * 1000}")

    print(f"Total de linhas processadas: {len(data)}")
    return pd.DataFrame(data)

def inserir_no_banco(df, table_name, columns, create_table_query, create_tipo_query):
    conn = None
    cursor = None
    try:
        database_url = environ.get("DB_URL")
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()

        # Criar ou ajustar tabela tipo
        cursor.execute("DELETE FROM tipo WHERE nome = 'producao';")  # Remover 'producao'
        cursor.execute(create_tipo_query)
        conn.commit()
        print("Tabela tipo ajustada com sucesso.")

        # Criar ou ajustar tabela exportacao
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
        insert_query = f"INSERT INTO {table_name_lower} ({', '.join(columns)}) VALUES ({', '.join(['%s'] * len(columns))}) ON CONFLICT DO NOTHING;"
        rows_inserted = 0
        for _, row in df.iterrows():
            values = (int(row['ano']), int(row['idTipo']), int(row['idEspecie']), float(row['receita']), float(row['volume']))
            cursor.execute(insert_query, values)
            rows_inserted += 1
        conn.commit()
        print(f"Dados inseridos com sucesso em {table_name_lower}! Linhas inseridas: {rows_inserted}")

        cursor.execute(f"SELECT COUNT(*) FROM {table_name_lower};")
        count = cursor.fetchone()[0]
        print(f"Total de linhas na tabela {table_name_lower} após inserção: {count}")
        cursor.execute(f"SELECT * FROM {table_name_lower} LIMIT 5;")
        print("Primeiras 5 linhas da tabela exportacao:", cursor.fetchall())

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
    df_exportacao = processar_exportacao()
    inserir_no_banco(
        df_exportacao, "Exportacao", ["ano", "idTipo", "idEspecie", "receita", "volume"],
        """
        CREATE TABLE Exportacao (
            ano INT NOT NULL,
            idTipo INT NOT NULL,
            idEspecie INT NOT NULL,
            receita NUMERIC(14,2),
            volume NUMERIC(14,2),
            PRIMARY KEY (ano, idTipo, idEspecie),
            FOREIGN KEY (idTipo) REFERENCES tipo(idTipo),
            FOREIGN KEY (idEspecie) REFERENCES especie(idEspecie)
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS tipo (
            idTipo INT PRIMARY KEY,
            nome VARCHAR(50) NOT NULL
        );
        INSERT INTO tipo (idTipo, nome) VALUES
        (1, 'Verde'),
        (2, 'Torrado'),
        (3, 'Solúvel')
        ON CONFLICT (idTipo) DO UPDATE SET nome = EXCLUDED.nome;
        """
    )