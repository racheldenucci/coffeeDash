import requests
import os
import pdfplumber
import pandas as pd
import re

# URL direta do PDF
pdf_url = "https://www.cecafe.com.br/site/wp-content/uploads/graficos/CECAFE-ExportacaoMensal_PaisDestino.pdf"
pdf_name = pdf_url.split("/")[-1]
pdf_folder = "pdfs_cecafe"
pdf_path = os.path.join(pdf_folder, pdf_name)

# Criar pasta se não existir
os.makedirs(pdf_folder, exist_ok=True)

# Baixar o PDF se ainda não existir
if not os.path.exists(pdf_path):
    print(f"📥 Baixando {pdf_name}...")
    response = requests.get(pdf_url)
    with open(pdf_path, "wb") as f:
        f.write(response.content)
    print("✅ Download concluído.")
else:
    print("📂 PDF já existe localmente.")

# Extrair dados do PDF
dados = []

with pdfplumber.open(pdf_path) as pdf:
    for page in pdf.pages:
        text = page.extract_text()
        lines = text.split("\n")
        for line in lines:
            # Ignorar linhas que não contêm dados
            if re.match(r"^(Exporta|01/2025|TOTAL|13/03/2025|Página|\d{1,2}/\d{2}/\d{4}|^\s*$)", line.strip()):
                continue
            # Se a linha tiver números no formato de milhares, é uma linha de dados
            if re.search(r"\d{1,3}[.,]\d{3}", line):
                nome_e_numeros = re.findall(r"[^\d]+|\d[\d.,]*", line)
                nome = ""
                numeros = []
                for item in nome_e_numeros:
                    if re.match(r"\d", item):
                        numeros.append(item.replace(".", "").replace(",", "."))
                    else:
                        nome += item.strip() + " "
                nome = nome.strip()
                if len(numeros) >= 2:
                    dados.append([nome] + numeros)

# Criar DataFrame
num_colunas = len(dados[0]) - 1
colunas = ["País"] + [f"{m:02d}/2025" for m in range(1, num_colunas)] + ["Total"]
df = pd.DataFrame(dados, columns=colunas)

# Converter colunas numéricas
for col in colunas[1:]:
    df[col] = pd.to_numeric(df[col], errors="coerce")

# Salvar como CSV
# output_csv = "exportacoes_cecafe_reconstruido.csv"
# df.to_csv(output_csv, index=False)
# print(f"✅ Dados salvos com sucesso em '{output_csv}'.")

# Visualização opcional
print("\n📊 Primeiras linhas do DataFrame:")
print(df.head())
