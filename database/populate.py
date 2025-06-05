import psycopg2
import os
from dotenv import load_dotenv
from scraping.scraper_abic import (
    clean_exportacao_volume,
    clean_exportacao_receita,
    clean_exportacao_preco_medio,
    clean_preco_varejo,
    clean_producao,
    get_table_from_abic,
    URLS
)


load_dotenv()

DB_URL = os.getenv("DB_URL")

def insert_if_not_exists(cur, table, column, value, id_column='id'):
    cur.execute(f"SELECT {id_column} FROM {table} WHERE {column} = %s", (value,))
    row = cur.fetchone()
    if row:
        return row[0]
    cur.execute(f"INSERT INTO {table} ({column}) VALUES (%s) RETURNING {id_column}", (value,))
    return cur.fetchone()[0]

def populate_aux_tables(cur, df_producao):
    tipos_fixos = ['Verde', 'Torrado', 'Moído']
    for tipo in tipos_fixos:
        insert_if_not_exists(cur, 'tipo', 'descricao', tipo, 'idTipo')

    estados = df_producao['Estado'].unique()
    regioes = df_producao[['Regiao', 'Estado']].drop_duplicates()
    especies = df_producao['Especie'].unique() if 'Especie' in df_producao.columns else ['Arábica']

    for estado in estados:
        insert_if_not_exists(cur, 'estado', 'descricao', estado, 'idEstado')

    for _, row in regioes.iterrows():
        id_estado = insert_if_not_exists(cur, 'estado', 'descricao', row['Estado'], 'idEstado')
        cur.execute("SELECT idRegiao FROM regiao WHERE descricao = %s AND idEstado = %s", (row['Regiao'], id_estado))
        if not cur.fetchone():
            cur.execute("INSERT INTO regiao (descricao, idEstado) VALUES (%s, %s)", (row['Regiao'], id_estado))

    for especie in especies:
        insert_if_not_exists(cur, 'especie', 'descricao', especie, 'idEspecie')

    for pais in ['Alemanha', 'Estados Unidos']:
        insert_if_not_exists(cur, 'pais', 'descricao', pais, 'idPais')

def get_id(cur, table, column, value, id_column='id'):
    cur.execute(f"SELECT {id_column} FROM {table} WHERE {column} = %s", (value,))
    row = cur.fetchone()
    if not row:
        raise ValueError(f"{value} não encontrado em {table}")
    return row[0]

def insert_producao(cur, df):
    for _, row in df.iterrows():
        id_estado = get_id(cur, "estado", "descricao", row['Estado'], "idEstado")
        id_regiao = get_id(cur, "regiao", "descricao", row['Regiao'], "idRegiao")
        id_tipo = get_id(cur, "tipo", "descricao", row['TipoCafe'], "idTipo")
        especie_nome = row['Especie'] if 'Especie' in row else 'Arábica'
        id_especie = get_id(cur, "especie", "descricao", especie_nome, "idEspecie")

        cur.execute("""
            INSERT INTO producao (ano, idEstado, idRegiao, idTipo, idEspecie, area, volume)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT DO NOTHING
        """, (row['Ano'], id_estado, id_regiao, id_tipo, id_especie, row['Area'], row['Volume']))

def insert_preco_varejo(cur, df):
    for _, row in df.iterrows():
        cur.execute("""
            INSERT INTO precovarejo (mes, ano, valor)
            VALUES (%s, %s, %s)
            ON CONFLICT DO NOTHING
        """, (row['Mes'], row['Ano'], row['Preco']))

def insert_exportacao(cur, df):
    id_tipo = get_id(cur, "tipo", "descricao", "Verde", "idTipo")
    id_especie = get_id(cur, "especie", "descricao", "Arábica", "idEspecie")
    for _, row in df.iterrows():
        cur.execute("""
            INSERT INTO exportacao (ano, idTipo, idEspecie, receita, volume)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT DO NOTHING
        """, (row['Ano'], id_tipo, id_especie, row.get('Receita', 0), row.get('Volume', 0)))

def main():
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()

    try:
        df_vol = clean_exportacao_volume(get_table_from_abic(URLS["export_volume"]))
        df_rec = clean_exportacao_receita(get_table_from_abic(URLS["export_receita"]))
        df_exp = df_vol.merge(df_rec, on=["Ano", "Mes"], how="left")
        df_preco_varejo = clean_preco_varejo(get_table_from_abic(URLS["preco_varejo"]))
        df_producao = clean_producao(get_table_from_abic(URLS["producao"]))

        populate_aux_tables(cur, df_producao)
        insert_exportacao(cur, df_exp)
        insert_producao(cur, df_producao)
        insert_preco_varejo(cur, df_preco_varejo)

        conn.commit()
        print("Banco populado com sucesso")

    except Exception as e:
        print(f"Erro: {e}")
        conn.rollback()

    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    main()
