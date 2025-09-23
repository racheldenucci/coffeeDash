import pandas as pd
import psycopg2
from psycopg2 import Error
from os import environ
from dotenv import load_dotenv

# Carregar variáveis de ambiente do arquivo .env
load_dotenv()

def processar_producao():
    # Processar dados de área
    df_area = pd.read_excel("data/producaoArea.xlsx", sheet_name="Plan1", header=4)
    # Processar dados de volume
    df_volume = pd.read_excel("data/producaoTotal.xlsx", sheet_name="Plan1", header=4)
    data = []
    anos = [year for year in range(2001, 2024)]

    print("Colunas disponíveis em producaoArea.xlsx:", df_area.columns.tolist())
    print("Colunas disponíveis em producaoTotal.xlsx:", df_volume.columns.tolist())

    estado_map = {
        "AM": 1, "RO": 2, "PA": 3, "BA": 4, "MT": 5, "GO": 6, "MG": 7, "ES": 8,
        "RJ": 9, "SP": 10, "PR": 11, "OUTROS": 12
    }
    # Mapeamento de regiões com base nos dados inseridos na tabela Regiao
    regiao_map = {
        "Cerrado": 1, "Planalto": 2, "Atlântico": 3,
        "Sul e Centro-Oeste": 4, "Triângulo, Alto Paranaíba e Noroeste": 5,
        "Zona da Mata, Rio Doce e Central": 6, "Norte, Jequitinhona e Mucuri": 7
    }

    for index, row in df_area.iterrows():
        estado_col = "Estados e Regiões"
        especie_col = "Espécie"
        if pd.isna(row[estado_col]) or pd.isna(row[especie_col]):
            continue

        estado = row[estado_col]
        if estado == "BRASIL":
            continue

        especie_regiao = row[especie_col]
        if "Sub-total" in str(especie_regiao):
            continue

        if isinstance(especie_regiao, str) and " - " in especie_regiao:
            regiao_desc, especie_desc = especie_regiao.split(" - ")
        else:
            regiao_desc = None
            especie_desc = especie_regiao

        id_estado = estado_map.get(estado, None)
        if id_estado is None:
            continue
        id_regiao = regiao_map.get(regiao_desc, None) if regiao_desc and regiao_desc in regiao_map else None
        id_especie = 1 if especie_desc == "Arábica" else 2 if especie_desc == "Robusta" else 3 if especie_desc == "Conillon" else None
        id_tipo = 1

        if id_especie and id_estado:
            for ano in anos:
                area = row[ano] if pd.notna(row[ano]) and ano in df_area.columns else None
                # Obter o volume correspondente da outra planilha
                volume_row = df_volume.iloc[index]
                volume = volume_row[ano] if pd.notna(row[ano]) and ano in df_volume.columns else None
                if area is not None or volume is not None:
                    # Converter diretamente para tipos nativos do Python
                    data.append({
                        "ano": int(ano) if ano is not None else None,
                        "idEstado": int(id_estado),
                        "idRegiao": int(id_regiao) if id_regiao is not None else None,
                        "idTipo": int(id_tipo),
                        "idEspecie": int(id_especie),
                        "area": float(area) if area is not None else None,
                        "volume": float(volume) if volume is not None else None
                    })
                    print(f"Processando linha {index}, estado {estado}, região {regiao_desc}, ano {ano}, area {area}, volume {volume}, especie {especie_desc}")

    print(f"Total de linhas processadas: {len(data)}")
    return pd.DataFrame(data)

def inserir_no_banco(df, table_name, columns, create_table_query):
    conn = None
    cursor = None
    try:
        database_url = environ.get("DB_URL")
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        
        table_name_lower = table_name.lower()
        
        cursor.execute("SELECT EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = %s)", (table_name_lower,))
        table_exists = cursor.fetchone()[0]
        
        if not table_exists:
            print(f"Tabela {table_name_lower} não existe, criando...")
            cursor.execute(create_table_query.replace(table_name, table_name_lower))
            conn.commit()  # Commit a criação da tabela
        else:
            print(f"Tabela {table_name_lower} já existe, truncando dados...")
            cursor.execute(f"TRUNCATE TABLE {table_name_lower} RESTART IDENTITY CASCADE;")
            conn.commit()  # Commit o truncate

        # Garantir que os valores sejam passados como tipos nativos do Python
        insert_query = f"INSERT INTO {table_name_lower} ({', '.join(columns)}) VALUES ({', '.join(['%s'] * len(columns))}) ON CONFLICT DO NOTHING;"
        rows_inserted = 0
        for _, row in df.iterrows():
            values = []
            for col in columns:
                value = row[col]
                if pd.isna(value):
                    values.append(None)
                elif col == 'ano':
                    values.append(int(value))
                elif col in ['area', 'volume']:
                    values.append(float(value))
                else:
                    values.append(int(value) if value is not None else None)
            cursor.execute(insert_query, tuple(values))
            rows_inserted += 1
        conn.commit()
        print(f"Dados inseridos com sucesso em {table_name_lower}! Linhas inseridas: {rows_inserted}")
        
        cursor.execute(f"SELECT COUNT(*) FROM {table_name_lower};")
        count = cursor.fetchone()[0]
        print(f"Total de linhas na tabela {table_name_lower} após inserção: {count}")
        cursor.execute(f"SELECT * FROM {table_name_lower} LIMIT 5;")
        print(f"Primeiras 5 linhas da tabela {table_name_lower}:", cursor.fetchall())
        
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
    conn = None
    try:
        database_url = environ.get("DB_URL")
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()

        cursor.execute("DROP TABLE IF EXISTS Regiao CASCADE;")
        cursor.execute("DROP TABLE IF EXISTS Tipo CASCADE;")
        cursor.execute("DROP TABLE IF EXISTS Especie CASCADE;")
        cursor.execute("DROP TABLE IF EXISTS Estado CASCADE;")

        cursor.execute("""
            CREATE TABLE Estado (
                idEstado INT PRIMARY KEY,
                descricao VARCHAR(100)
            );
        """)
        for id_estado, descricao in [
            (1, 'AM'), (2, 'RO'), (3, 'PA'), (4, 'BA'), (5, 'MT'),
            (6, 'GO'), (7, 'MG'), (8, 'ES'), (9, 'RJ'), (10, 'SP'),
            (11, 'PR'), (12, 'OUTROS')
        ]:
            cursor.execute("INSERT INTO Estado (idEstado, descricao) VALUES (%s, %s) ON CONFLICT DO NOTHING;", (id_estado, descricao))
        conn.commit()
        cursor.execute("SELECT * FROM Estado;")
        result = cursor.fetchall()
        if result:
            print("Estado(s) confirmado(s):")
            for row in result:
                print(f"idEstado: {row[0]}, descricao: {row[1]}")
        else:
            print("Falha ao inserir em Estado.")
        print("Conteúdo da tabela Estado:", result)

        cursor.execute("""
            CREATE TABLE Especie (
                idEspecie INT PRIMARY KEY,
                nome VARCHAR(50)
            );
        """)
        cursor.execute("INSERT INTO Especie (idEspecie, nome) VALUES (1, 'Arábica');")
        cursor.execute("INSERT INTO Especie (idEspecie, nome) VALUES (2, 'Robusta');")
        cursor.execute("INSERT INTO Especie (idEspecie, nome) VALUES (3, 'Conillon');")
        conn.commit()
        cursor.execute("SELECT * FROM Especie;")
        result = cursor.fetchall()
        if result:
            print("Espécie(s) confirmada(s):")
            for row in result:
                print(f"idEspecie: {row[0]}, nome: {row[1]}")
        else:
            print("Falha ao inserir em Especie.")
        print("Conteúdo da tabela Especie:", result)

        cursor.execute("""
            CREATE TABLE Tipo (
                idTipo INT PRIMARY KEY,
                nome VARCHAR(50)
            );
        """)
        cursor.execute("INSERT INTO Tipo (idTipo, nome) VALUES (1, 'Verde');")
        cursor.execute("INSERT INTO Tipo (idTipo, nome) VALUES (2, 'Torrado');")
        cursor.execute("INSERT INTO Tipo (idTipo, nome) VALUES (3, 'Solúvel');")
        conn.commit()
        cursor.execute("SELECT * FROM Tipo;")
        result = cursor.fetchall()
        if result:
            print("Tipo(s) confirmado(s):")
            for row in result:
                print(f"idTipo: {row[0]}, nome: {row[1]}")
        else:
            print("Falha ao inserir em Tipo.")
        print("Conteúdo da tabela Tipo:", result)

        cursor.execute("""
            CREATE TABLE Regiao (
                idRegiao INT PRIMARY KEY,
                idEstado INT,
                nome VARCHAR(50),
                FOREIGN KEY (idEstado) REFERENCES Estado(idEstado)
            );
        """)
        # Inserir regiões manualmente com base na saída fornecida
        regioes = [
            (1, 4, 'Cerrado'),
            (2, 4, 'Planalto'),
            (3, 4, 'Atlântico'),
            (4, 7, 'Sul e Centro-Oeste'),
            (5, 7, 'Triângulo, Alto Paranaíba e Noroeste'),
            (6, 7, 'Zona da Mata, Rio Doce e Central'),
            (7, 7, 'Norte, Jequitinhona e Mucuri')
        ]
        for id_regiao, id_estado, nome in regioes:
            cursor.execute(
                "INSERT INTO Regiao (idRegiao, idEstado, nome) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING;",
                (id_regiao, id_estado, nome)
            )
        conn.commit()
        cursor.execute("SELECT * FROM Regiao;")
        result = cursor.fetchall()
        if result:
            print("Região(ões) confirmada(s):")
            for row in result:
                print(f"idRegiao: {row[0]}, idEstado: {row[1]}, nome: {row[2]}")
        else:
            print("Falha ao inserir em Regiao.")
        print("Conteúdo da tabela Regiao:", result)

        conn.commit()

    except Error as e:
        print(f"Erro ao criar/popular tabelas: {e.__class__.__name__}: {str(e)}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

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