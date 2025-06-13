import pandas as pd
import psycopg2
from psycopg2 import Error
from os import environ
from dotenv import load_dotenv

# Carregar variáveis de ambiente do arquivo .env
load_dotenv()

def processar_producao():
    df = pd.read_excel("data/producaoArea.xlsx", sheet_name="Plan1", header=4)
    data = []
    anos = [year for year in range(2001, 2024)]

    # Depuração: listar colunas disponíveis
    print("Colunas disponíveis em producaoArea.xlsx:", df.columns.tolist())

    # Mapeamento simples de estados (ajustar conforme a planilha)
    estado_map = {"Brasil": 1}  # Exemplo: mapeia "Brasil" para idEstado = 1

    for index, row in df.iterrows():
        estado_col = "Estados e Regiões"
        especie_col = "Espécie"
        if pd.isna(row[estado_col]) or pd.isna(row[especie_col]):
            continue

        estado = row[estado_col]
        especie_regiao = row[especie_col]
        if "Sub-total" in str(especie_regiao):
            continue

        if isinstance(especie_regiao, str) and " - " in especie_regiao:
            regiao_desc, especie_desc = especie_regiao.split(" - ")
        else:
            regiao_desc = None
            especie_desc = especie_regiao

        # Mapeamento de idEstado (ajustar conforme os dados da planilha)
        id_estado = estado_map.get(estado, 1)  # Usa 1 como padrão se o estado não estiver mapeado
        id_regiao = None  # Sem região específica por enquanto
        id_especie = 1 if especie_desc == "Arábica" else 2 if especie_desc == "Robusta" else None
        id_tipo = 1  # Tipo genérico para produção

        if id_especie and id_estado:
            for ano in anos:
                area = row[ano] if pd.notna(row[ano]) and ano in df.columns else None
                if area is not None:
                    data.append({"ano": ano, "idEstado": id_estado, "idRegiao": id_regiao, "idTipo": id_tipo, "idEspecie": id_especie, "area": float(area), "volume": None})
                    print(f"Processando linha {index}, estado {estado}, ano {ano}, area {area}, especie {especie_desc}")  # Depuração

    print(f"Total de linhas processadas: {len(data)}")
    return pd.DataFrame(data)

def inserir_no_banco(df, table_name, columns, create_table_query):
    conn = None
    try:
        database_url = environ.get("DB_URL")
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        cursor.execute(create_table_query)
        # Converter para float nativo antes de inserir, lidando com nulos
        for col in ['ano', 'area', 'volume']:
            if col in df.columns:
                df[col] = df[col].fillna(0).astype(float).apply(float)
        insert_query = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({', '.join(['%s'] * len(columns))}) ON CONFLICT DO NOTHING;"
        rows_inserted = 0
        for _, row in df.iterrows():
            cursor.execute(insert_query, tuple(row[col] for col in columns))
            rows_inserted += 1
        conn.commit()
        print(f"Dados inseridos com sucesso em {table_name}! Linhas inseridas: {rows_inserted}")
    except Error as e:
        print(f"Erro ao inserir no banco em {table_name}: {e}")
    finally:
        if conn:
            cursor.close()
            conn.close()

if __name__ == "__main__":
    # Conexão ao banco
    conn = None
    try:
        database_url = environ.get("DB_URL")
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()

        # Dropar e recriar tabelas para garantir a estrutura correta
        cursor.execute("DROP TABLE IF EXISTS Producao CASCADE;")
        cursor.execute("DROP TABLE IF EXISTS Regiao CASCADE;")
        cursor.execute("DROP TABLE IF EXISTS Tipo CASCADE;")
        cursor.execute("DROP TABLE IF EXISTS Especie CASCADE;")
        cursor.execute("DROP TABLE IF EXISTS Estado CASCADE;")

        # Criar e popular tabela Estado
        cursor.execute("""
            CREATE TABLE Estado (
                idEstado INT PRIMARY KEY,
                descricao VARCHAR(100)
            );
        """)
        cursor.execute("INSERT INTO Estado (idEstado, descricao) VALUES (1, 'Brasil');")
        conn.commit()  # Commit após inserção
        cursor.execute("SELECT * FROM Estado;")
        result = cursor.fetchall()
        if result:
            print("Estado(s) confirmado(s):")
            for row in result:
                print(f"idEstado: {row[0]}, descricao: {row[1]}")
        else:
            print("Falha ao inserir em Estado.")
        print("Conteúdo da tabela Estado:", result)

        # Criar e popular tabela Especie
        cursor.execute("""
            CREATE TABLE Especie (
                idEspecie INT PRIMARY KEY,
                nome VARCHAR(50)
            );
        """)
        cursor.execute("INSERT INTO Especie (idEspecie, nome) VALUES (1, 'Arábica');")
        cursor.execute("INSERT INTO Especie (idEspecie, nome) VALUES (2, 'Robusta');")
        conn.commit()  # Commit após inserção
        cursor.execute("SELECT * FROM Especie;")
        result = cursor.fetchall()
        if result:
            print("Espécie(s) confirmada(s):")
            for row in result:
                print(f"idEspecie: {row[0]}, nome: {row[1]}")
        else:
            print("Falha ao inserir em Especie.")
        print("Conteúdo da tabela Especie:", result)

        # Criar e popular tabela Tipo
        cursor.execute("""
            CREATE TABLE Tipo (
                idTipo INT PRIMARY KEY,
                nome VARCHAR(50)
            );
        """)
        cursor.execute("INSERT INTO Tipo (idTipo, nome) VALUES (1, 'Produção');")
        conn.commit()  # Commit após inserção
        cursor.execute("SELECT * FROM Tipo;")
        result = cursor.fetchall()
        if result:
            print("Tipo(s) confirmado(s):")
            for row in result:
                print(f"idTipo: {row[0]}, nome: {row[1]}")
        else:
            print("Falha ao inserir em Tipo.")
        print("Conteúdo da tabela Tipo:", result)

        # Criar tabela Regiao (opcional, sem dados por enquanto)
        cursor.execute("""
            CREATE TABLE Regiao (
                idRegiao INT PRIMARY KEY,
                idEstado INT,
                nome VARCHAR(50),
                FOREIGN KEY (idEstado) REFERENCES Estado(idEstado)
            );
        """)
        print("Tabela Regiao criada (vazia por enquanto)")

        conn.commit()

    except Error as e:
        print(f"Erro ao criar/popular tabelas: {e}")
    finally:
        if conn:
            cursor.close()
            conn.close()

    # Processar e inserir dados em Producao
    df_producao = processar_producao()
    inserir_no_banco(df_producao, "Producao", ["ano", "idEstado", "idRegiao", "idTipo", "idEspecie", "area", "volume"], """
        CREATE TABLE Producao (
            ano INT NOT NULL,
            idEstado INT NOT NULL,
            idRegiao INT,
            idTipo INT NOT NULL,
            idEspecie INT NOT NULL,
            area NUMERIC(12,2),
            volume NUMERIC(12,2),
            PRIMARY KEY (ano, idEstado, idTipo, idEspecie),
            FOREIGN KEY (idEstado) REFERENCES Estado(idEstado),
            FOREIGN KEY (idRegiao) REFERENCES Regiao(idRegiao),
            FOREIGN KEY (idTipo) REFERENCES Tipo(idTipo),
            FOREIGN KEY (idEspecie) REFERENCES Especie(idEspecie)
        );
    """)