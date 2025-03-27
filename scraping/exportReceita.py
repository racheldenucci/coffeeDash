#SCRAPER ABIC/EXPORTAÇÕES POR RECEITA

import requests
import pandas as pd
from bs4 import BeautifulSoup

url = "https://estatisticas.abic.com.br/estatisticas/exportacoes-brasileiras-de-cafe-receita/"

payload = {}
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

response = requests.request("GET", url, headers=headers, data=payload)

if response.status_code == 200:
    soup = BeautifulSoup(response.text, 'html.parser')
    
    table = soup.find('table')
    
    if table is None:
        print("Error: no table found")
        print(soup.prettify())  #mostra o HTML
        exit()
    
    #extrai cabeçalhos
    headers = [header.text.strip() for header in table.find_all('th')]
    print("found headers:", headers)  #debug
    
    # cria cabeçalho genérico se não houver
    if not headers:
        print("Nenhum cabeçalho encontrado. Usando cabeçalhos genéricos.")
    
    #extrai dados da tabela
    data = []
    for row in table.find_all('tr')[1:]:  #pula a primeira linha
        cols = [col.text.strip() for col in row.find_all('td')]
        if cols: 
            data.append(cols)
    
    #debug: número de colunas nos dados
    if data:
        print(f"colunas nos dados: {len(data[0])}")
        print("primeira linha de dados:", data[0])
    
    #ajusta cabeçalhos 
    if not headers and data:
        headers = [f"Coluna_{i+1}" for i in range(len(data[0]))]
    
    
    if data and len(headers) != len(data[0]):
        print(f"Ajustando cabeçalhos: {len(headers)} cabeçalhos vs {len(data[0])} colunas de dados")
        headers = [f"Coluna_{i+1}" for i in range(len(data[0]))]
    
    #criar o df
    try:
        df = pd.DataFrame(data, columns=headers)
        print("\nDataFrame criado com sucesso: ")
        print(df)
        
        
    except Exception as e:
        print(f"Erro ao criar DataFrame: {e}")
        print("Dados brutos:", data) #debug
else:
    print(f"Erro de requisição: {response.status_code}")