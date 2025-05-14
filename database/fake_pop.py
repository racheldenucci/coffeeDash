import os
from dotenv import load_dotenv
import psycopg2

load_dotenv()
DB_URL = os.getenv("DB_URL")


def insert_tabelas_auxiliares(cur):
    tipos = ['Verde', 'Moído']
    especies = ['Arábica', 'Conilon']
    paises = ['Alemanha', 'Estados Unidos']
    estados = ['Minas Gerais', 'São Paulo']
    regioes = [('Sul de Minas', 'Minas Gerais'), ('Alta Mogiana', 'São Paulo')]

    for tipo in tipos:
        cur.execute("INSERT INTO tipo (descricao) VALUES (%s) ON CONFLICT DO NOTHING", (tipo,))
    for especie in especies:
        cur.execute("INSERT INTO especie (descricao) VALUES (%s) ON CONFLICT DO NOTHING", (especie,))
    for pais in paises:
        cur.execute("INSERT INTO pais (descricao) VALUES (%s) ON CONFLICT DO NOTHING", (pais,))
    for estado in estados:
        cur.execute("INSERT INTO estado (descricao) VALUES (%s) ON CONFLICT DO NOTHING", (estado,))
    for regiao, estado_nome in regioes:
        cur.execute("SELECT idEstado FROM estado WHERE descricao = %s", (estado_nome,))
        id_estado = cur.fetchone()
        if id_estado:
            cur.execute("""
                INSERT INTO regiao (descricao, idEstado) 
                VALUES (%s, %s) 
                ON CONFLICT DO NOTHING
            """, (regiao, id_estado[0]))

def get_id(cur, table, column, value, id_column='id'):
    cur.execute(f"SELECT {id_column} FROM {table} WHERE {column} = %s", (value,))
    result = cur.fetchone()
    if result:
        return result[0]
    else:
        raise ValueError(f"{value} não encontrado em {table}")

def insert_dados_principais(cur):
    import random

    # mapeia os IDs
    id_tipo_verde = get_id(cur, 'tipo', 'descricao', 'Verde', 'idTipo')
    id_tipo_moido = get_id(cur, 'tipo', 'descricao', 'Moído', 'idTipo')
    id_esp_arabica = get_id(cur, 'especie', 'descricao', 'Arábica', 'idEspecie')
    id_esp_conilon = get_id(cur, 'especie', 'descricao', 'Conilon', 'idEspecie')
    id_pais_de = get_id(cur, 'pais', 'descricao', 'Alemanha', 'idPais')
    id_pais_us = get_id(cur, 'pais', 'descricao', 'Estados Unidos', 'idPais')
    id_estado_mg = get_id(cur, 'estado', 'descricao', 'Minas Gerais', 'idEstado')
    id_estado_sp = get_id(cur, 'estado', 'descricao', 'São Paulo', 'idEstado')
    id_regiao_mg = get_id(cur, 'regiao', 'descricao', 'Sul de Minas', 'idRegiao')
    id_regiao_sp = get_id(cur, 'regiao', 'descricao', 'Alta Mogiana', 'idRegiao')

    # PRODUCAO
    producoes = [
        (2023, id_estado_mg, id_regiao_mg, id_tipo_verde, id_esp_arabica, 100000, 50000),
        (2023, id_estado_sp, id_regiao_sp, id_tipo_moido, id_esp_conilon, 80000, 45000),
    ]
    for linha in producoes:
        cur.execute("""
            INSERT INTO producao (ano, idEstado, idRegiao, idTipo, idEspecie, area, volume)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT DO NOTHING
        """, linha)

    # EXPORTACAO
    exportacoes = [
        (2023, id_tipo_verde, id_esp_arabica, 9000000, 70000),
        (2023, id_tipo_moido, id_esp_conilon, 6000000, 50000),
    ]
    for linha in exportacoes:
        cur.execute("""
            INSERT INTO exportacao (ano, idTipo, idEspecie, receita, volume)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT DO NOTHING
        """, linha)

    # DESTINO
    destinos = [
        (2023, 1, id_esp_arabica, id_pais_de, 30000),
        (2023, 2, id_esp_arabica, id_pais_us, 40000),
    ]
    for linha in destinos:
        cur.execute("""
            INSERT INTO destino (ano, mes, idEspecie, idPais, volume)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT DO NOTHING
        """, linha)

    # CONSUMO_INTERNO
    consumos = [
        (2023, id_tipo_verde, 75000),
        (2022, id_tipo_moido, 82000)
    ]
    for linha in consumos:
        cur.execute("""
            INSERT INTO consumointerno (ano, tipo, volume)
            VALUES (%s, %s, %s)
            ON CONFLICT DO NOTHING
        """, linha)

    # PRECO_VAREJO
    precos = [
        (1, 2023, 21.5),
        (2, 2023, 22.0),
        (3, 2023, 22.8),
    ]
    for linha in precos:
        cur.execute("""
            INSERT INTO precovarejo (mes, ano, valor)
            VALUES (%s, %s, %s)
            ON CONFLICT DO NOTHING
        """, linha)

def main():
    try:
        conn = psycopg2.connect(DB_URL)
        cur = conn.cursor()

        insert_tabelas_auxiliares(cur)
        insert_dados_principais(cur)

        conn.commit()
        print("✅ Banco populado com dados de teste.")

    except Exception as e:
        print("❌ Erro:", e)
        conn.rollback()

    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    main()
