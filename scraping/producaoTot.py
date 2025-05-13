import requests
import pandas as pd
from bs4 import BeautifulSoup

def get_producao():
    url = "https://estatisticas.abic.com.br/estatisticas/producao-agricola-2/"

    payload = {}
    headers = {
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        # 'accept-language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7,es;q=0.6,la;q=0.5',
        # 'cache-control': 'max-age=0',
        # 'priority': 'u=0, i',
        # 'referer': 'https://estatisticas.abic.com.br/',
        # 'sec-ch-ua': '"Chromium";v="134", "Not:A-Brand";v="24", "Google Chrome";v="134"',
        # 'sec-ch-ua-mobile': '?0',
        # 'sec-ch-ua-platform': '"Windows"',
        # 'sec-fetch-dest': 'document',
        # 'sec-fetch-mode': 'navigate',
        # 'sec-fetch-site': 'same-origin',
        # 'sec-fetch-user': '?1',
        # 'upgrade-insecure-requests': '1',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36'
    }

    response = requests.get(url, headers=headers, data=payload)

    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        
        
        tables = soup.find_all('table')
        if not tables:
            print("Erro: nenhuma tabela encontrada.")
            print(soup.prettify())
            return
        
        # Itera sobre cada tabela encontrada
        for idx, table in enumerate(tables, start=1):
            # Extrai os cabeçalhos
            headers_table = [th.get_text(strip=True) for th in table.find_all('th')]
            print(f"Tabela {idx}: cabeçalhos encontrados:", headers_table)
            
            # Extrai os dados das linhas (pula a primeira linha se ela for o cabeçalho)
            data = []
            for row in table.find_all('tr')[1:]:
                cols = [td.get_text(strip=True) for td in row.find_all('td')]
                if cols:
                    data.append(cols)
            
            # Se não houver cabeçalhos ou se a quantidade não bater, cria cabeçalhos genéricos
            if not headers_table and data:
                headers_table = [f"Coluna_{i+1}" for i in range(len(data[0]))]
            if data and len(headers_table) != len(data[0]):
                headers_table = [f"Coluna_{i+1}" for i in range(len(data[0]))]
            
            # Cria o DataFrame e salva em CSV
            # try:
            #     df = pd.DataFrame(data, columns=headers_table)
            #     print(f"\nDataFrame da tabela {idx} criado com sucesso:")
            #     print(df.head())
            #     df.to_csv(f'tabela_{idx}.csv', index=False, encoding='utf-8')
            # except Exception as e:
            #     print(f"Erro ao criar DataFrame para a tabela {idx}: {e}")
            #     print("Dados brutos:", data)
    else:
        print(f"Erro de requisição: {response.status_code}")

