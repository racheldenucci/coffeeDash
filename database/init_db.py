import psycopg2

DB_URL = 'postgres://ua2s8fta7iiqu:pe16a9baec7a8e7104e3d3e1c99a56bfc3625f91a944eeac0e3b7d3eee5c1090e@c6sfjnr30ch74e.cluster-czrs8kj4isg7.us-east-1.rds.amazonaws.com:5432/df6vcs0bs7fbr'

def create_tables(cur):
    cur.execute("""
    CREATE TABLE IF NOT EXISTS Tipo (
        idTipo SERIAL PRIMARY KEY,
        descricao VARCHAR(100) UNIQUE NOT NULL
    );

    CREATE TABLE IF NOT EXISTS Especie (
        idEspecie SERIAL PRIMARY KEY,
        descricao VARCHAR(100) UNIQUE NOT NULL
    );

    CREATE TABLE IF NOT EXISTS Pais (
        idPais SERIAL PRIMARY KEY,
        descricao VARCHAR(100) UNIQUE NOT NULL
    );

    CREATE TABLE IF NOT EXISTS Estado (
        idEstado SERIAL PRIMARY KEY,
        descricao VARCHAR(100) UNIQUE NOT NULL
    );

    CREATE TABLE IF NOT EXISTS Regiao (
        idRegiao SERIAL PRIMARY KEY,
        descricao VARCHAR(100) NOT NULL,
        idEstado INT NOT NULL,
        FOREIGN KEY (idEstado) REFERENCES estado(idEstado)
    );

    CREATE TABLE IF NOT EXISTS Producao (
        ano INT NOT NULL,
        idEstado INT NOT NULL,
        idRegiao INT,
        idTipo INT NOT NULL,
        idEspecie INT NOT NULL,
        area NUMERIC(12,2),
        volume NUMERIC(12,2),
        PRIMARY KEY (ano, idEstado, idTipo, idEspecie),
        FOREIGN KEY (idEstado) REFERENCES estado(idEstado),
        FOREIGN KEY (idRegiao) REFERENCES regiao(idRegiao),
        FOREIGN KEY (idTipo) REFERENCES tipo(idTipo),
        FOREIGN KEY (idEspecie) REFERENCES especie(idEspecie)
    );

    CREATE TABLE IF NOT EXISTS Exportacao (
        ano INT NOT NULL,
        idTipo INT NOT NULL,
        idEspecie INT NOT NULL,
        receita NUMERIC(14,2),
        volume NUMERIC(14,2),
        PRIMARY KEY (ano, idTipo, idEspecie),
        FOREIGN KEY (idTipo) REFERENCES tipo(idTipo),
        FOREIGN KEY (idEspecie) REFERENCES especie(idEspecie)
    );

    CREATE TABLE IF NOT EXISTS Destino (
        ano INT NOT NULL,
        mes INT NOT NULL,
        idEspecie INT NOT NULL,
        idPais INT NOT NULL,
        volume NUMERIC(12,2),
        PRIMARY KEY (ano, mes, idEspecie, idPais),
        FOREIGN KEY (idEspecie) REFERENCES especie(idEspecie),
        FOREIGN KEY (idPais) REFERENCES pais(idPais)
    );

    CREATE TABLE IF NOT EXISTS ConsumoInterno (
        ano INT PRIMARY KEY,
        tipo INT NOT NULL,
        volume NUMERIC(12,2),
        FOREIGN KEY (tipo) REFERENCES tipo(idTipo)
    );

    CREATE TABLE IF NOT EXISTS PrecoVarejo (
        mes INT NOT NULL,
        ano INT NOT NULL,
        valor NUMERIC(10,2),
        PRIMARY KEY (mes, ano)
    );
    """)

def main():
    try:
        conn = psycopg2.connect(DB_URL)
        cur = conn.cursor()

        create_tables(cur)

        conn.commit()
        print("Tabelas criadas e dados auxiliares inseridos com sucesso.")
    
    except Exception as e:
        print("Erro:", e)
        conn.rollback()
    
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    main()
