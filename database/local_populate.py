import pandas as pd
import psycopg2
from psycopg2 import Error
from os import environ
import datetime
from dotenv import load_dotenv

# Carregar variáveis de ambiente do arquivo .env
load_dotenv()

# Função para processar exportações
def processar_exportacao():
    df_volume = pd.read_excel("data/exportacoes.xlsx", sheet_name="VOLUME (SACAS)", header=[0, 1])
    df_receita = pd.read_excel("data/exportacoes.xlsx", sheet_name="RECEITA CAMBIAL (US$ MIL)", header=[0, 1])
    data = []

    # Depuração: listar todas as colunas disponíveis
    print("Colunas de df_volume:", df_volume.columns.tolist())
    
    # Extrair anos a partir da coluna 'Mês/Ano'
    anos = set()
    for mes_ano in df_volume[('VOLUME (em sacas de 60 Kg)', 'Mês/Ano')].dropna():
        if isinstance(mes_ano, str):
            try:
                mes, ano = mes_ano.split('/')
                anos.add(int(ano))
            except ValueError:
                continue
    anos = sorted(anos)

    print("Anos detectados:", anos)  # Depuração

    for ano_int in anos:
        ano = str(ano_int)
        volume_conillon = df_volume[("VOLUME (em sacas de 60 Kg)", ano)]["Conillon"].sum() if (ano in [col[1] for col in df_volume.columns]) else 0
        volume_arabica = df_volume[("VOLUME (em sacas de 60 Kg)", ano)]["Arábica"].sum() if (ano in [col[1] for col in df_volume.columns]) else 0
        volume_torrado = df_volume[("Torrado", ano)]["Total"].sum() if (ano in [col[1] for col in df_volume.columns]) else 0
        volume_solivel = df_volume[("Solúvel", ano)]["Total"].sum() if (ano in [col[1] for col in df_volume.columns]) else 0

        receita_conillon = df_receita[("RECEITA CAMBIAL (em US$ 1000)", ano)]["Conillon"].sum() if (ano in [col[1] for col in df_receita.columns]) else 0
        receita_arabica = df_receita[("RECEITA CAMBIAL (em US$ 1000)", ano)]["Arábica"].sum() if (ano in [col[1] for col in df_receita.columns]) else 0
        receita_torrado = df_receita[("Torrado", ano)]["Total"].sum() if (ano in [col[1] for col in df_receita.columns]) else 0
        receita_solivel = df_receita[("Solúvel", ano)]["Total"].sum() if (ano in [col[1] for col in df_receita.columns]) else 0

        # Mapeamento simples de idEspecie
        id_especie_conillon = 1
        id_especie_arabica = 2
        id_especie_torrado = None
        id_especie_solivel = None

        data.append({"ano": ano_int, "idTipo": 1, "idEspecie": id_especie_conillon, "receita": float(receita_conillon), "volume": float(volume_conillon)})
        data.append({"ano": ano_int, "idTipo": 1, "idEspecie": id_especie_arabica, "receita": float(receita_arabica), "volume": float(volume_arabica)})
        data.append({"ano": ano_int, "idTipo": 2, "idEspecie": id_especie_torrado, "receita": float(receita_torrado), "volume": float(volume_torrado)})
        data.append({"ano": ano_int, "idTipo": 3, "idEspecie": id_especie_solivel, "receita": float(receita_solivel), "volume": float(volume_solivel)})

    return pd.DataFrame(data)

# Função para processar preço varejo
def processar_preco_varejo():
    df = pd.read_excel("data/precoVarejo.xlsx", sheet_name="Página1", skiprows=1)
    data = []
    month_map = {
        'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
        'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
    }  # Ajustado para inglês

    # Depuração: listar colunas disponíveis
    print("Colunas disponíveis em precoVarejo.xlsx:", df.columns.tolist())

    mes_ano_col = "Mês/Ano"
    valor_col = "Tradicional"

    if mes_ano_col not in df.columns or valor_col not in df.columns:
        raise KeyError(f"Colunas '{mes_ano_col}' ou '{valor_col}' não encontradas. Verifique a planilha.")

    for index, row in df.iterrows():
        mes_ano = row[mes_ano_col]
        if pd.notna(mes_ano):
            if isinstance(mes_ano, pd.Timestamp) or isinstance(mes_ano, datetime.datetime):
                mes_ano_str = mes_ano.strftime('%b/%y').lower()
            else:
                mes_ano_str = str(mes_ano).lower()
            
            try:
                mes_str, ano_str = mes_ano_str.split('/')
                mes = month_map.get(mes_str[:3])
                if mes is None:
                    print(f"Formato de mês inválido em '{mes_ano_str}', pulando...")
                    continue
                ano = int(ano_str)
            except (ValueError, AttributeError):
                print(f"Formato inválido em '{mes_ano_str}', pulando...")
                continue
            
            valor = row[valor_col] if pd.notna(row[valor_col]) else None
            if valor is not None:
                data.append({"mes": mes, "ano": ano, "valor": float(valor)})

    return pd.DataFrame(data)

# Função para processar produção
def processar_producao():
    df = pd.read_excel("data/producaoArea.xlsx", sheet_name="Plan1", header=4)
    data = []
    anos = [year for year in range(2001, 2024)]  # Usar inteiros diretamente

    # Depuração: listar colunas disponíveis
    print("Colunas disponíveis em producaoArea.xlsx:", df.columns.tolist())

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

        id_estado = 1  # Exemplo: substitua por lógica real
        id_regiao = None  # Substitua por mapeamento real de Regiao
        id_especie = 1 if especie_desc == "Arábica" else 2 if especie_desc == "Robusta" else None
        id_tipo = 1  # Exemplo: assumindo produção como tipo 1

        if id_especie and id_estado:
            for ano in anos:
                area = row[ano] if pd.notna(row[ano]) and ano in df.columns else None
                if area is not None:
                    data.append({"ano": ano, "idEstado": id_estado, "idRegiao": id_regiao, "idTipo": id_tipo, "idEspecie": id_especie, "area": float(area), "volume": None})

    return pd.DataFrame(data)

# Função para processar produção total
def processar_producao_total():
    df = pd.read_excel("data/producaoTotal.xlsx", sheet_name="Plan1", skiprows=2)
    data = []
    anos = [year for year in range(2001, 2024)]

    # Depuração: listar colunas disponíveis
    print("Colunas disponíveis em producaoTotal.xlsx:", df.columns.tolist())

    for index, row in df.iterrows():
        estado_col = "Unnamed: 0"
        especie_col = "Unnamed: 1"
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

        id_estado = 1  # Exemplo: substitua por lógica real
        id_regiao = None  # Substitua por mapeamento real de Regiao
        id_especie = 1 if especie_desc == "Arábica" or especie_desc == "Arabica" else 2 if especie_desc == "Robusta" else None
        id_tipo = 1  # Exemplo: assumindo produção como tipo 1

        if id_especie and id_estado:
            for ano in anos:
                volume = row[ano] if pd.notna(row[ano]) and ano in df.columns else None
                if volume is not None:
                    data.append({"ano": ano, "idEstado": id_estado, "idRegiao": id_regiao, "idTipo": id_tipo, "idEspecie": id_especie, "area": None, "volume": float(volume)})

    return pd.DataFrame(data)

# Função para processar consumo interno
def processar_consumo_interno():
    df = pd.read_excel("data/consumoInterno.xlsx", sheet_name="Sheet1")
    data = []
    
    for index, row in df.iterrows():
        ano = row["Ano"] if pd.notna(row["Ano"]) else None
        if ano is not None:
            torrado_moido = row["Somente Torrado / Moído"] if pd.notna(row["Somente Torrado / Moído"]) else None
            total_soluvel = row["Total Inclusive Solúvel (milhões de sacas)"] if pd.notna(row["Total Inclusive Solúvel (milhões de sacas)"]) else None
            volume = (float(torrado_moido) + float(total_soluvel)) * 1000000 if torrado_moido is not None and total_soluvel is not None else None
            tipo = 1  # Exemplo: tipo 1 para torrado/moído

            if volume is not None:
                data.append({"ano": int(ano), "tipo": tipo, "volume": float(volume)})

    return pd.DataFrame(data)

# Função genérica para inserir no banco
def inserir_no_banco(df, table_name, columns, create_table_query):
    conn = None
    try:
        database_url = environ.get("DB_URL")
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        cursor.execute(create_table_query)
        # Converter para float nativo antes de inserir, lidando com nulos
        for col in ['mes', 'ano', 'valor', 'receita', 'volume', 'area']:
            if col in df.columns:
                df[col] = df[col].fillna(0).astype(float).apply(float)  # Substituir nulos por 0 e converter
        insert_query = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({', '.join(['%s'] * len(columns))}) ON CONFLICT DO NOTHING;"
        for _, row in df.iterrows():
            cursor.execute(insert_query, tuple(row[col] for col in columns))
        conn.commit()
        print(f"Dados inseridos com sucesso em {table_name}!")
    except Error as e:
        print(f"Erro ao inserir no banco em {table_name}: {e}")
    finally:
        if conn:
            cursor.close()
            conn.close()

# Execução
if __name__ == "__main__":
    df_exportacao = processar_exportacao()
    inserir_no_banco(df_exportacao, "Exportacao", ["ano", "idTipo", "idEspecie", "receita", "volume"], """
        CREATE TABLE IF NOT EXISTS Exportacao (
            ano INT NOT NULL,
            idTipo INT NOT NULL,
            idEspecie INT NOT NULL,
            receita NUMERIC(14,2),
            volume NUMERIC(14,2),
            PRIMARY KEY (ano, idTipo, idEspecie),
            FOREIGN KEY (idTipo) REFERENCES Tipo(idTipo),
            FOREIGN KEY (idEspecie) REFERENCES Especie(idEspecie)
        );
    """)

    df_preco_varejo = processar_preco_varejo()
    inserir_no_banco(df_preco_varejo, "PrecoVarejo", ["mes", "ano", "valor"], """
        CREATE TABLE IF NOT EXISTS PrecoVarejo (
            mes INT NOT NULL,
            ano INT NOT NULL,
            valor NUMERIC(10,2),
            PRIMARY KEY (mes, ano)
        );
    """)

    df_producao = processar_producao()
    inserir_no_banco(df_producao, "Producao", ["ano", "idEstado", "idRegiao", "idTipo", "idEspecie", "area", "volume"], """
        CREATE TABLE IF NOT EXISTS Producao (
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

    df_producao_total = processar_producao_total()
    inserir_no_banco(df_producao_total, "Producao", ["ano", "idEstado", "idRegiao", "idTipo", "idEspecie", "area", "volume"], """
        CREATE TABLE IF NOT EXISTS Producao (
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

    df_consumo_interno = processar_consumo_interno()
    inserir_no_banco(df_consumo_interno, "ConsumoInterno", ["ano", "tipo", "volume"], """
        CREATE TABLE IF NOT EXISTS ConsumoInterno (
            ano INT PRIMARY KEY,
            tipo INT NOT NULL,
            volume NUMERIC(12,2),
            FOREIGN KEY (tipo) REFERENCES Tipo(idTipo)
        );
    """)