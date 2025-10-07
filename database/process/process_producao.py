import pandas as pd
import psycopg2
from psycopg2 import Error
from os import environ
from dotenv import load_dotenv
import re
import unicodedata


# CONGIF

AREA_XLSX_PATH = "data/producaoArea.xlsx"
VOLUME_XLSX_PATH = "data/producaoTotal.xlsx"
SHEET_NAME = "Plan1"
HEADER_ROW = 4  # linha de cabeçalho (0-based)


# NORMALIZAÇÃO

def norm_text(s: str) -> str:
    s = str(s or "").strip()
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode('ascii')
    return s

def extrai_sigla(estado_raw: str) -> str:
    """
    Aceita formatos como 'Minas Gerais (MG)', 'MG', 'MG ' ou 'Outros'.
    Retorna a sigla quando possível, senão um texto upper sem espaços.
    """
    e = norm_text(estado_raw).upper()
    m = re.search(r'\(([A-Z]{2})\)', e)  #pega só a sigla mesmo se tiver entre parenteses
    if m:
        return m.group(1)
    e = e.replace(' ', '')
    if re.fullmatch(r'[A-Z]{2}', e):
        return e
    return e 

def map_especie(x: str):
    t = norm_text(x).lower()
    if 'arabica' in t:
        return 1 
    if 'robusta' in t:
        return 2  
    if 'conilon' in t or 'conillon' in t:
        return 3  
    return None

def anos_disponiveis(df: pd.DataFrame):
    out = []
    for c in df.columns:
        cs = str(c)
        if cs.isdigit():
            out.append(int(cs))
    return sorted(set(out))



def processar_producao():
    print("Lendo planilhas...")
    df_area = pd.read_excel(AREA_XLSX_PATH,  sheet_name=SHEET_NAME, header=HEADER_ROW)
    df_vol  = pd.read_excel(VOLUME_XLSX_PATH, sheet_name=SHEET_NAME, header=HEADER_ROW)

    #ano = int
    area_year_map = {c: int(c) for c in df_area.columns if str(c).isdigit()}
    vol_year_map  = {c: int(c) for c in df_vol.columns  if str(c).isdigit()}
    df_area = df_area.rename(columns=area_year_map)
    df_vol  = df_vol.rename(columns=vol_year_map)

    anos = sorted(set(anos_disponiveis(df_area)) | set(anos_disponiveis(df_vol)))
    print(f"Anos detectados: {anos}")

    ESTADO_COL  = "Estados e Regiões"
    ESPECIE_COL = "Espécie"

    #limpa linhas inválidas
    for name, df in (("área", df_area), ("volume", df_vol)):
        if ESTADO_COL not in df.columns or ESPECIE_COL not in df.columns:
            raise ValueError(f"A planilha de {name} não contém as colunas '{ESTADO_COL}' e '{ESPECIE_COL}'. Verifique o header= e o sheet_name.")
        df["_ESTADO_SIGLA"] = df[ESTADO_COL].apply(extrai_sigla)
        df["_ESPECIE_RAW"]  = df[ESPECIE_COL].astype(str).str.strip()

        mask_valid = (
            df[ESTADO_COL].notna()
            & df[ESPECIE_COL].notna()
            & (~df[ESTADO_COL].astype(str).str.contains(r'BRASIL', case=False, na=False))
            & (~df[ESPECIE_COL].astype(str).str.contains(r'Sub-total|\[object Object\]', case=False, na=False))
        )
        skipped = df.loc[~mask_valid, [ESTADO_COL, ESPECIE_COL]].head(5)
        if len(skipped):
            print(f"Aviso: {len(df) - mask_valid.sum()} linha(s) descartada(s) por filtros em planilha de {name}. Exemplos:\n{skipped}")
        df.drop(index=df.index[~mask_valid], inplace=True)

    
    keep_area = ["_ESTADO_SIGLA", "_ESPECIE_RAW"] + [a for a in anos if a in df_area.columns]
    keep_vol  = ["_ESTADO_SIGLA", "_ESPECIE_RAW"] + [a for a in anos if a in df_vol.columns]
    area_m = df_area[keep_area].copy()
    vol_m  = df_vol[keep_vol].copy()

    
    area_long = area_m.melt(
        id_vars=["_ESTADO_SIGLA", "_ESPECIE_RAW"],
        value_vars=[c for c in area_m.columns if isinstance(c, int)],
        var_name="ano", value_name="area"
    )
    vol_long = vol_m.melt(
        id_vars=["_ESTADO_SIGLA", "_ESPECIE_RAW"],
        value_vars=[c for c in vol_m.columns if isinstance(c, int)],
        var_name="ano", value_name="volume"
    )

    
    wide = area_long.merge(vol_long, on=["_ESTADO_SIGLA", "_ESPECIE_RAW", "ano"], how="outer")

    
    estado_map = {
        "AM": 1, "RO": 2, "PA": 3, "BA": 4, "MT": 5, "GO": 6, "MG": 7, "ES": 8,
        "RJ": 9, "SP": 10, "PR": 11, "OUTROS": 12, "AC": 13, "AL": 14, "AP": 15,
        "CE": 16, "DF": 17, "MA": 18, "MS": 19, "PE": 20, "PI": 21, "RN": 22,
        "RS": 23, "RR": 24, "SC": 25, "SE": 26, "TO": 27
    }

    wide["idEstado"]  = wide["_ESTADO_SIGLA"].map(estado_map)
    wide["idEspecie"] = wide["_ESPECIE_RAW"].apply(map_especie)
    wide["idTipo"]    = 1  # Verde (ajuste se necessário)

    # limpa linhas sem mapeamento/sem dados
    before = len(wide)
    wide = wide[(wide["idEstado"].notna()) & (wide["idEspecie"].notna()) & (wide[["area", "volume"]].notna().any(axis=1))]
    after = len(wide)
    print(f"Registros válidos (com estado/especie e pelo menos área/volume): {after} (descartados: {before - after})")

    # Converte tipos base
    wide["ano"]       = wide["ano"].astype(int)
    wide["idEstado"]  = wide["idEstado"].astype(int)
    wide["idTipo"]    = wide["idTipo"].astype(int)
    wide["idEspecie"] = wide["idEspecie"].astype(int)


    df = (wide
          .groupby(["ano", "idEstado", "idTipo", "idEspecie"], as_index=False)[["area", "volume"]]
          .sum(min_count=1))

    df = df.sort_values(["ano", "idEstado", "idEspecie"]).reset_index(drop=True)
    print(f"Total de linhas agregadas para inserção: {len(df)}")
    return df



def inserir_no_banco(df, table_name, columns, create_table_query):
    conn = None
    cursor = None
    try:
        database_url = environ.get("DB_URL")
        if not database_url:
            raise RuntimeError("Variável de ambiente DB_URL não encontrada. Defina-a no .env ou no ambiente.")

        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()

        table_name_lower = table_name.lower()
        cursor.execute(
            "SELECT EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = %s)",
            (table_name_lower,)
        )
        table_exists = cursor.fetchone()[0]

        if not table_exists:
            print(f"Tabela {table_name_lower} não existe, criando...")
            cursor.execute(create_table_query.replace(table_name, table_name_lower))
            conn.commit()
        else:
            print(f"Tabela {table_name_lower} já existe, truncando dados...")
            cursor.execute(f"TRUNCATE TABLE {table_name_lower} RESTART IDENTITY CASCADE;")
            conn.commit()

        insert_query = f"""
            INSERT INTO {table_name_lower} ({', '.join(columns)})
            VALUES ({', '.join(['%s'] * len(columns))})
            ON CONFLICT DO NOTHING;
        """
        rows_inserted = 0
        for _, row in df.iterrows():
            values = []
            for col in columns:
                value = row[col] if col in row else None
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
        print(f"Dados inseridos com sucesso em {table_name_lower}! Linhas (tentadas) inseridas: {rows_inserted}")

        cursor.execute(f"SELECT COUNT(*) FROM {table_name_lower};")
        count = cursor.fetchone()[0]
        print(f"Total de linhas na tabela {table_name_lower} após inserção: {count}")

        cursor.execute(f"SELECT * FROM {table_name_lower} ORDER BY ano, idEstado, idEspecie LIMIT 5;")
        print("Primeiras 5 linhas:", cursor.fetchall())

    except Error as e:
        print(f"Erro ao inserir no banco em {table_name_lower}: {e.__class__.__name__}: {str(e)}")
        if conn:
            conn.rollback()
            print("Transação revertida.")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

if __name__ == "__main__":
    load_dotenv()

    conn = None
    cursor = None
    try:
        database_url = environ.get("DB_URL")
        if not database_url:
            raise RuntimeError("Variável de ambiente DB_URL não encontrada. Defina-a no .env ou no ambiente.")
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()

        
        cursor.execute("DROP TABLE IF EXISTS Producao CASCADE;")
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
            (11, 'PR'), (12, 'OUTROS'), (13, 'AC'), (14, 'AL'),
            (15, 'AP'), (16, 'CE'), (17, 'DF'), (18, 'MA'), (19, 'MS'),
            (20, 'PE'), (21, 'PI'), (22, 'RN'), (23, 'RS'), (24, 'RR'),
            (25, 'SC'), (26, 'SE'), (27, 'TO'), (28, 'PB')
        ]:
            cursor.execute(
                "INSERT INTO Estado (idEstado, descricao) VALUES (%s, %s) ON CONFLICT DO NOTHING;",
                (id_estado, descricao)
            )


        cursor.execute("""
            CREATE TABLE Especie (
                idEspecie INT PRIMARY KEY,
                nome VARCHAR(50)
            );
        """)
        cursor.execute("INSERT INTO Especie (idEspecie, nome) VALUES (1, 'Arábica');")
        cursor.execute("INSERT INTO Especie (idEspecie, nome) VALUES (2, 'Robusta');")
        cursor.execute("INSERT INTO Especie (idEspecie, nome) VALUES (3, 'Conillon');")


        cursor.execute("""
            CREATE TABLE Tipo (
                idTipo INT PRIMARY KEY,
                nome VARCHAR(50)
            );
        """)
        cursor.execute("INSERT INTO Tipo (idTipo, nome) VALUES (1, 'Verde');")
        cursor.execute("INSERT INTO Tipo (idTipo, nome) VALUES (2, 'Torrado');")
        cursor.execute("INSERT INTO Tipo (idTipo, nome) VALUES (3, 'Solúvel');")


        cursor.execute("""
            CREATE TABLE Regiao (
                idRegiao INT PRIMARY KEY,
                idEstado INT,
                nome VARCHAR(50),
                FOREIGN KEY (idEstado) REFERENCES Estado(idEstado)
            );
        """)
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


        cursor.execute("""
            CREATE TABLE Producao (
                ano INT NOT NULL,
                idEstado INT NOT NULL,
                idRegiao INT, -- opcional (fica sempre NULL neste pipeline agregado)
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

        conn.commit()
        print("Tabelas criadas/populadas com sucesso.")

    except Error as e:
        print(f"Erro ao criar/popular tabelas: {e.__class__.__name__}: {str(e)}")
        if conn:
            conn.rollback()
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


    df_producao = processar_producao()


    inserir_no_banco(
        df_producao,
        "Producao",
        ["ano", "idEstado", "idRegiao", "idTipo", "idEspecie", "area", "volume"],
        """
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
        """
    )

    print("Fim.")
