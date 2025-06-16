import pandas as pd
import psycopg2
from psycopg2 import Error
from os import environ
from dotenv import load_dotenv
import pdfplumber
import re

# Carregar variáveis de ambiente do arquivo .env
load_dotenv()

def is_valid_string(s):
    # Aceita strings com letras, números, espaços e alguns caracteres especiais comuns
    return bool(s and not s.isdigit() and re.match(r'^[a-zA-Z0-9\s\-\&\(\)\.,\'\u00C0-\u00FF]+$', s))

def processar_paises(cursor):
    # Inserir países a partir dos PDFs
    paises = set()
    for pdf_path in ["data/destino2024.pdf", "data/destino2025.pdf"]:
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        print(f"Texto extraído de {pdf_path}: {text[:200]}...")
                        lines = text.split('\n')
                        start_data = False
                        for line in lines:
                            if "Exportação entre" in line:
                                start_data = True
                                continue
                            if start_data and line.strip():
                                columns = [col.strip() for col in line.split() if col.strip()]  # Usar espaço como delimitador
                                if columns and len(columns) > 1 and is_valid_string(columns[0]):
                                    pais = columns[0].strip()
                                    paises.add(pais)
                                    print(f"Pais detectado: {pais}")
        except Exception as e:
            print(f"Erro ao processar {pdf_path}: {e.__class__.__name__}: {str(e)}")
            continue
    for pais in paises:
        if pais:
            try:
                cursor.execute("INSERT INTO pais (descricao) VALUES (%s) ON CONFLICT (descricao) DO NOTHING;", (pais,))
                print(f"Pais inserido ou existente: {pais}")
            except Error as e:
                print(f"Erro ao inserir pais {pais}: {e.__class__.__name__}: {str(e)}")
    return

def processar_pdf_exportacao(pdf_path, ano, cursor):
    # Processar dados de exportação do PDF
    data = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    print(f"Texto extraído de {pdf_path} para exportação: {text[:200]}...")
                    lines = text.split('\n')
                    start_data = False
                    for i, line in enumerate(lines):
                        if "Exportação entre" in line:
                            start_data = True
                            # Próxima linha contém os meses
                            month_line = lines[i + 1].strip().split()
                            months = [m for m in month_line if m and not m.isdigit()]  # Capturar meses (ex.: "01/2024")
                            continue
                        if start_data and line.strip() and i > i + 1:  # Dados começam após os meses
                            columns = [col.strip() for col in line.split() if col.strip()]
                            if columns and len(columns) > 1 and is_valid_string(columns[0]):
                                pais = columns[0].strip()
                                meses = columns[1:]  # Volumes a partir da segunda coluna
                                for mes_idx, volume in enumerate(meses, 1):
                                    volume = volume.replace(',', '').replace('.', '').strip() if volume else '0'
                                    if volume and volume != '0':
                                        try:
                                            volume = float(volume)
                                            cursor.execute("SELECT idPais FROM pais WHERE descricao = %s;", (pais,))
                                            id_pais = cursor.fetchone()
                                            if id_pais:
                                                id_pais = id_pais[0]
                                                data.append({
                                                    "ano": ano,
                                                    "mes": mes_idx,
                                                    "idPais": id_pais,
                                                    "volume": volume
                                                })
                                                print(f"Processando {ano}-{mes_idx:02d}, {pais}, volume {volume}, idPais {id_pais}")
                                        except ValueError:
                                            print(f"Valor inválido ignorado: {pais}, mês {mes_idx}, volume {volume}")
    except Exception as e:
        print(f"Erro ao processar {pdf_path}: {e.__class__.__name__}: {str(e)}")
    print(f"Total de linhas processadas para {ano}: {len(data)}")
    return pd.DataFrame(data)

def processar_exportacoes(conn):
    cursor = conn.cursor()
    # Inserir países primeiro
    processar_paises(cursor)
    conn.commit()

    # Processar os dois PDFs
    df_2024 = processar_pdf_exportacao("data/destino2024.pdf", 2024, cursor)
    df_2025 = processar_pdf_exportacao("data/destino2025.pdf", 2025, cursor)
    df_exportacao = pd.concat([df_2024, df_2025], ignore_index=True)
    return df_exportacao

def inserir_no_banco(df, table_name, columns, create_table_query, conn):
    cursor = conn.cursor()
    try:
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
            values = (int(row['ano']), int(row['mes']), int(row['idPais']), float(row['volume']))
            cursor.execute(insert_query, values)
            rows_inserted += 1
        conn.commit()
        print(f"Dados inseridos com sucesso em {table_name_lower}! Linhas inseridas: {rows_inserted}")

        cursor.execute(f"SELECT COUNT(*) FROM {table_name_lower};")
        count = cursor.fetchone()[0]
        print(f"Total de linhas na tabela {table_name_lower} após inserção: {count}")
        cursor.execute(f"SELECT * FROM {table_name_lower} ORDER BY ano, mes, idPais LIMIT 5;")
        print("Primeiras 5 linhas da tabela destino:", cursor.fetchall())

    except Error as e:
        print(f"Erro ao inserir no banco em {table_name_lower}: {e.__class__.__name__}: {str(e)}")
        conn.rollback()
        print("Transação revertida. Tentando verificar estado da tabela...")
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {table_name_lower};")
            count = cursor.fetchone()[0] if cursor.rowcount >= 0 else 0
            print(f"Linhas na tabela {table_name_lower} após erro: {count}")
        except Error as e2:
            print(f"Falha ao verificar tabela após erro: {e2.__class__.__name__}: {str(e2)}")
    finally:
        cursor.close()

if __name__ == "__main__":
    conn = psycopg2.connect(environ.get("DB_URL"))
    df_exportacao = processar_exportacoes(conn)
    inserir_no_banco(df_exportacao, "Destino", ["ano", "mes", "idPais", "volume"],
                     """
                     CREATE TABLE Destino (
                         ano INT NOT NULL,
                         mes INT NOT NULL,
                         idPais INT NOT NULL,
                         volume NUMERIC(12,2),
                         PRIMARY KEY (ano, mes, idPais),
                         FOREIGN KEY (idPais) REFERENCES pais(idPais)
                     );
                     """, conn)
    conn.close()