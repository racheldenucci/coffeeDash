import requests
import pandas as pd
from bs4 import BeautifulSoup

def get_export_volume():
    url = "https://estatisticas.abic.com.br/estatisticas/exportacoes-brasileiras-de-cafe-volume/"

    headers = {
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'accept-language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7,es;q=0.6,la;q=0.5',
        'cache-control': 'max-age=0',
        'priority': 'u=0, i',
        'referer': 'https://estatisticas.abic.com.br/',
        'sec-ch-ua': '"Chromium";v="134", "Not:A-Brand";v="24", "Google Chrome";v="134"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'document',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-site': 'same-origin',
        'sec-fetch-user': '?1',
        'upgrade-insecure-requests': '1',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36'
    }

    try:
        response = requests.get(url, headers=headers)
    except Exception as e:
        print(f"Erro ao fazer requisição: {e}")
        return pd.DataFrame()

    if response.status_code != 200:
        print(f"Erro de requisição: {response.status_code}")
        return pd.DataFrame()

    soup = BeautifulSoup(response.text, 'html.parser')
    table = soup.find('table')

    if table is None:
        print("Erro: Nenhuma tabela encontrada.")
        return pd.DataFrame()

    #extrai cabeçalhos
    headers = [header.text.strip() for header in table.find_all('th')]
    if not headers:
        print("Nenhum cabeçalho encontrado. Usando cabeçalhos genéricos.")

    #extrai dados
    data = []
    for row in table.find_all('tr')[1:]:
        cols = [col.text.strip() for col in row.find_all('td')]
        if cols:
            data.append(cols)

    if not data:
        print("Nenhum dado encontrado na tabela.")
        return pd.DataFrame()

    # Ajusta os cabeçalhos se necessário
    if not headers or len(headers) != len(data[0]):
        headers = [f"Coluna_{i+1}" for i in range(len(data[0]))]

    try:
        df = pd.DataFrame(data, columns=headers)
        df['Fonte'] = 'ABIC - Exportações por Volume'
        return df
    except Exception as e:
        print(f"Erro ao criar DataFrame: {e}")
        return pd.DataFrame()
