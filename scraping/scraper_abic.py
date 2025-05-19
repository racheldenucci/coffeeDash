import requests
import pandas as pd
from bs4 import BeautifulSoup

# Dicionário com as URLs das tabelas
URLS = {
    "export_preco_medio": "https://estatisticas.abic.com.br/estatisticas/exportacoes-brasileiras-de-cafe-preco-medio/",
    "export_receita": "https://estatisticas.abic.com.br/estatisticas/exportacoes-brasileiras-de-cafe-receita/",
    "export_volume": "https://estatisticas.abic.com.br/estatisticas/exportacoes-brasileiras-de-cafe-volume/",
    "preco_varejo": "https://estatisticas.abic.com.br/estatisticas/preco-no-varejo/",
    "producao": "https://estatisticas.abic.com.br/estatisticas/producao-agricola-2/"
}

# Função genérica para extrair a tabela
def get_table_from_abic(url):
    response = requests.get(url)
    response.raise_for_status()
    soup = BeautifulSoup(response.content, 'html.parser')
    table = soup.find("table")
    return pd.read_html(str(table))[0]

# Funções de limpeza e transformação
def clean_exportacao_volume(df):
    df.columns = ['MesAno', 'Volume']
    df['MesAno'] = pd.to_datetime(df['MesAno'], format='%b/%Y', errors='coerce')
    df['Mes'] = df['MesAno'].dt.month
    df['Ano'] = df['MesAno'].dt.year
    df['Volume'] = df['Volume'].astype(str).str.replace('.', '', regex=False).str.replace(',', '.', regex=False).astype(float)
    return df[['Ano', 'Mes', 'Volume']]

def clean_exportacao_receita(df):
    df.columns = ['MesAno', 'Receita']
    df['MesAno'] = pd.to_datetime(df['MesAno'], format='%b/%Y', errors='coerce')
    df['Mes'] = df['MesAno'].dt.month
    df['Ano'] = df['MesAno'].dt.year
    df['Receita'] = df['Receita'].astype(str).str.replace('.', '', regex=False).str.replace(',', '.', regex=False).astype(float)
    return df[['Ano', 'Mes', 'Receita']]

def clean_exportacao_preco_medio(df):
    df.columns = ['MesAno', 'PrecoMedio']
    df['MesAno'] = pd.to_datetime(df['MesAno'], format='%b/%Y', errors='coerce')
    df['Mes'] = df['MesAno'].dt.month
    df['Ano'] = df['MesAno'].dt.year
    df['PrecoMedio'] = df['PrecoMedio'].astype(str).str.replace('.', '', regex=False).str.replace(',', '.', regex=False).astype(float)
    return df[['Ano', 'Mes', 'PrecoMedio']]

def clean_preco_varejo(df):
    df.columns = ['MesAno', 'Preco']
    df['MesAno'] = pd.to_datetime(df['MesAno'], format='%b/%Y', errors='coerce')
    df['Mes'] = df['MesAno'].dt.month
    df['Ano'] = df['MesAno'].dt.year
    df['Preco'] = df['Preco'].astype(str).str.replace('.', '', regex=False).str.replace(',', '.', regex=False).astype(float)
    return df[['Ano', 'Mes', 'Preco']]

def clean_producao(df):
    df.columns = ['Ano', 'Estado', 'Regiao', 'TipoCafe', 'Volume', 'Area']
    df['Volume'] = df['Volume'].astype(str).str.replace('.', '', regex=False).str.replace(',', '.', regex=False).astype(float)
    df['Area'] = df['Area'].astype(str).str.replace('.', '', regex=False).str.replace(',', '.', regex=False).astype(float)
    return df

# Exemplo de uso manual (opcional)
if __name__ == "__main__":
    df_vol = clean_exportacao_volume(get_table_from_abic(URLS["export_volume"]))
    df_rec = clean_exportacao_receita(get_table_from_abic(URLS["export_receita"]))
    df_preco = clean_exportacao_preco_medio(get_table_from_abic(URLS["export_preco_medio"]))
    df_varejo = clean_preco_varejo(get_table_from_abic(URLS["preco_varejo"]))
    df_producao = clean_producao(get_table_from_abic(URLS["producao"]))

    print(df_vol.head())
    print(df_rec.head())
    print(df_preco.head())
    print(df_varejo.head())
    print(df_producao.head())
