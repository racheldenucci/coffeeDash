import streamlit as st
import psycopg2
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
from dotenv import load_dotenv


load_dotenv()
DB_URL = os.getenv("DB_URL")

def get_dataframe(query):
    conn = psycopg2.connect(DB_URL)
    df = pd.read_sql(query, conn)
    conn.close()
    return df

st.set_page_config(page_title="Dashboard do Café", layout="wide")
st.title("☕ Dashboard de Dados do Café")

# 1. Produção por Estado
st.header("📈 Produção por Estado")
df_prod = get_dataframe("""
    SELECT e.descricao AS estado, SUM(p.volume) AS volumetotal
    FROM producao p
    JOIN estado e ON p.idEstado = e.idEstado
    GROUP BY e.descricao
    ORDER BY volumetotal DESC
""")
st.bar_chart(df_prod.set_index("estado"))

# 2. Exportação por Espécie
st.header("💵 Receita de Exportação por Espécie")
df_exp = get_dataframe("""
    SELECT es.descricao AS especie, SUM(e.receita) AS receitatotal
    FROM exportacao e
    JOIN especie es ON e.idEspecie = es.idEspecie
    GROUP BY es.descricao
    ORDER BY receitatotal DESC
""")
st.bar_chart(df_exp.set_index("especie"))

# 3. Destinos de Exportação
st.header("🌍 Exportações por País de Destino")
df_dest = get_dataframe("""
    SELECT pa.descricao AS pais, SUM(d.volume) AS volumetotal
    FROM destino d
    JOIN pais pa ON d.idPais = pa.idPais
    GROUP BY pa.descricao
    ORDER BY volumetotal DESC
""")
st.bar_chart(df_dest.set_index("pais"))

# 4. Evolução do Preço Médio no Varejo
st.header("🛒 Preço Médio no Varejo (R$/kg)")
df_preco = get_dataframe("""
    SELECT ano, mes, valor
    FROM precovarejo
    ORDER BY ano, mes
""")
df_preco['data'] = pd.to_datetime(df_preco['ano'].astype(str) + '-' + df_preco['mes'].astype(str), format='%Y-%m')
df_preco.set_index("data", inplace=True)
st.line_chart(df_preco['valor'])

# 5. Consumo Interno por Tipo
st.header("☕ Consumo Interno por Tipo de Café")
df_cons = get_dataframe("""
    SELECT t.descricao AS tipo, SUM(c.volume) AS consumototal
    FROM consumointerno c
    JOIN tipo t ON c.tipo = t.idTipo
    GROUP BY t.descricao
""")
st.bar_chart(df_cons.set_index("tipo"))
