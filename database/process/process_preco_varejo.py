import pandas as pd
import psycopg2
from psycopg2 import Error
from os import environ
from dotenv import load_dotenv
import re

# Carregar variáveis de ambiente do arquivo .env
load_dotenv()

def processar_preco_varejo():
    # Processar dados de preço de varejo
    df = pd.read_excel("data/precoVarejo.xlsx", sheet_name="Página1", header=1, dtype={'Tradicional': float})
    data = []

    print("Colunas disponíveis em precoVarejo.xlsx:", df.columns.tolist())
    print("Total de linhas no DataFrame:", len(df))

    # Mapear meses (abreviações para números)
    month_map = {
        'jan': 1, 'fev': 2, 'mar': 3, 'abr': 4, 'mai': 5, 'jun': 6,
        'jul': 7, 'ago': 8, 'set': 9, 'out': 10, 'nov': 11, 'dez': 12
    }

    for index, row in df.iterrows():
        mes_ano = row['Mês/Ano']
        valor = row['Tradicional']

        print(f"Linha {index} - Mês/Ano: {mes_ano}, Valor: {valor}")
        if pd.isna(mes_ano) or pd.isna(valor):
            print(f"Linha {index} ignorada (valor nulo): {mes_ano}, {valor}")
            continue

        # Tentar extrair mês e ano
        mes, ano = None, None
        mes_ano_str = str(mes_ano).strip().lower()

        # Caso 1: Formato "Mmm[/.]yy" (ex.: jan/97 ou jan./24)
        match_mmm_yy = re.match(r'(\w{3})(?:\.?)/(\d{2})', mes_ano_str)
        if match_mmm_yy:
            print(f"Debug - Mmm[/.]yy match: {mes_ano_str}")
            mes_str, ano_str = match_mmm_yy.groups()
            mes = month_map.get(mes_str)
            ano_num = int(ano_str)
            ano = 2000 + ano_num if ano_num <= 24 else 1900 + ano_num
            print(f"Debug - Parsed: mes={mes}, ano={ano}")
        # Caso 2: Formato "YYYY-MM-DD" ou "YYYY-MM-DD HH:MM:SS" (como texto) - mantido como backup
        elif re.match(r'^\d{4}-\d{2}-\d{2}(?: \d{2}:\d{2}:\d{2})?$', mes_ano_str):
            print(f"Debug - YYYY-MM-DD match: {mes_ano_str}")
            from datetime import datetime
            try:
                date_obj = datetime.strptime(mes_ano_str, '%Y-%m-%d %H:%M:%S' if ' ' in mes_ano_str else '%Y-%m-%d')
                mes = date_obj.month
                ano = date_obj.year
                print(f"Debug - Parsed: mes={mes}, ano={ano}")
            except ValueError as e:
                print(f"Debug - Erro ao parsear data: {e}")

        # Adicionar debug para validação
        if mes and ano:
            print(f"Debug - Validação: mes={mes}, ano={ano}, intervalo={1997 <= ano <= 2024}")
        if mes and ano and 1997 <= ano <= 2024:
            data.append({"mes": mes, "ano": ano, "valor": float(valor)})
            print(f"Processando linha {index}, mes {mes}, ano {ano}, valor {valor}")

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
        else:
            print(f"Tabela {table_name_lower} já existe, truncando dados...")
            cursor.execute(f"TRUNCATE TABLE {table_name_lower} RESTART IDENTITY CASCADE;")

        insert_query = f"INSERT INTO {table_name_lower} ({', '.join(columns)}) VALUES ({', '.join(['%s'] * len(columns))}) ON CONFLICT DO NOTHING;"
        rows_inserted = 0
        for _, row in df.iterrows():
            values = (int(row['mes']), int(row['ano']), float(row['valor']))
            cursor.execute(insert_query, values)
            rows_inserted += 1
        conn.commit()
        print(f"Dados inseridos com sucesso em {table_name_lower}! Linhas inseridas: {rows_inserted}")
        
        cursor.execute(f"SELECT COUNT(*) FROM {table_name_lower};")
        count = cursor.fetchone()[0]
        print(f"Total de linhas na tabela {table_name_lower} após inserção: {count}")
        cursor.execute(f"SELECT * FROM {table_name_lower} LIMIT 5;")
        print("Primeiras 5 linhas da tabela precovarejo:", cursor.fetchall())
        
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
    df_preco_varejo = processar_preco_varejo()
    inserir_no_banco(df_preco_varejo, "PrecoVarejo", ["mes", "ano", "valor"], """
        CREATE TABLE PrecoVarejo (
            mes INT NOT NULL,
            ano INT NOT NULL,
            valor NUMERIC(10,2),
            PRIMARY KEY (mes, ano)
        );
    """)