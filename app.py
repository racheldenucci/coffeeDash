import streamlit as st
import psycopg2
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import plotly_express as px
import os
from dotenv import load_dotenv


load_dotenv()
DB_URL = os.getenv("DB_URL")

def get_dataframe(query):
    conn = psycopg2.connect(DB_URL)
    df = pd.read_sql(query, conn)
    conn.close()
    return df

st.set_page_config(page_title="Dashboard do Café")
# st.title("☕ Dashboard de Dados do Café")

# col1, col2, col3, col4 = st.columns(4)
# anos = get_dataframe("SELECT DISTINCT ano FROM producao ORDER BY ano DESC")["ano"].tolist()  #RECONSIDERAR
# estados = get_dataframe("SELECT descricao FROM estado ORDER BY descricao")["descricao"].tolist()
# tipos = get_dataframe("SELECT nome FROM tipo ORDER BY nome")["nome"].tolist()
# especies = get_dataframe("SELECT nome FROM especie ORDER BY nome")["nome"].tolist()

# with col1:
#     ano_selecionado = st.selectbox("Selecione o Ano", anos, index=0)
# with col2:
#     estado_selecionado = st.selectbox("Selecione o Estado", ["Todos"] + estados, index=0)
# with col3:
#     tipo_selecionado = st.selectbox("Selecione o Tipo", ["Todos"] + tipos, index=0)
# with col4:    
#     especie_selecionada = st.selectbox("Selecione a Espécie", ["Todas"] + especies, index=0)

#Mapa de Produção por Estado
# 🗺️ Mapa de Produção por Estado (paleta "café" + escala log automática)
st.header("🗺️ Mapa de Produção por Estado")

conn = psycopg2.connect(DB_URL)
query = """
SELECT e.descricao AS estado, COALESCE(SUM(p.volume), 0) AS volume
FROM estado e
LEFT JOIN producao p ON e.idestado = p.idestado
GROUP BY e.descricao
ORDER BY e.descricao;
"""
df = pd.read_sql(query, conn)
conn.close()

# Paleta personalizada "café"
coffee_scale = [
    [0.00, "#f8f1e3"],  # creme (baixo)
    [0.30, "#d9a673"],  # caramelo
    [0.60, "#8b4513"],  # café
    [1.00, "#3e2723"],  # espresso (alto)
]

# Decide automaticamente se usa escala log
vol_min = float(df["volume"].replace(0, np.nan).min() or 0)
vol_max = float(df["volume"].max() or 0)
use_log = vol_max > 0 and (vol_max / max(vol_min, 1)) >= 20  # bem desigual? use log

df["volume_plot"] = df["volume"]
colorbar_title = "volume"
tickmode = None
tickvals = None
ticktext = None

if use_log:
    # log(1+x) para evitar -inf em zeros
    df["volume_plot"] = np.log1p(df["volume"]).astype(float)
    colorbar_title = "volume (log)"

    # colorbar com ticks “bonitos” mostrando os valores originais
    # 5 marcas geométricas entre 1 e vol_max (ajuste se quiser)
    if vol_max > 1:
        raw_ticks = np.geomspace(1, vol_max, 5)  # 1, …, max
        tickvals = np.log1p(raw_ticks)
        ticktext = [f"{int(t):,}".replace(",", ".") for t in raw_ticks]  # 1.000 etc.
        tickmode = "array"

fig = px.choropleth(
    df,
    geojson="https://raw.githubusercontent.com/codeforamerica/click_that_hood/master/public/data/brazil-states.geojson",
    locations="estado",               # usa siglas (MG, SP, …)
    featureidkey="properties.sigla",  # casa com a chave do geojson
    color="volume_plot",
    color_continuous_scale=coffee_scale,
    title="Produção de Café por Estado - Brasil",
)

fig.update_geos(fitbounds="locations", visible=False)

# Hover legível
fig.update_traces(
    hovertemplate="<b>%{location}</b><br>" +
                  "Volume: %{customdata} t<extra></extra>",
    customdata=[f"{int(v):,}".replace(",", ".") for v in df["volume"]]
)

# Colorbar e layout (bom no dark theme)
fig.update_layout(
    coloraxis_colorbar=dict(
        title=colorbar_title,
        thickness=16,
        tickmode=tickmode,
        tickvals=tickvals,
        ticktext=ticktext,
    ),
    margin=dict(l=0, r=0, t=60, b=0),
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
)

st.plotly_chart(fig, use_container_width=True)

# Volume Produzido por Estado e Ano
st.header("📊 Volume Produzido por Estado e Ano")

conn = psycopg2.connect(DB_URL)
query_volume_ano = """
SELECT p.ano, e.descricao AS estado, SUM(p.volume) AS volume
FROM producao p
JOIN estado e ON p.idestado = e.idestado
GROUP BY p.ano, e.descricao
ORDER BY p.ano, e.descricao;
"""
df_volume_ano = pd.read_sql(query_volume_ano, conn)
conn.close()

# Criar gráfico de barras empilhadas
fig_volume = px.bar(
    df_volume_ano,
    x="ano",
    y="volume",
    color="estado",
    title="Volume de Café Produzido por Estado ao Longo dos Anos",
    labels={"ano": "Ano", "volume": "Volume (toneladas)", "estado": "Estado"},
    barmode="stack",
    color_discrete_sequence=px.colors.qualitative.Set3
)

fig_volume.update_layout(
    xaxis=dict(tickmode='linear', dtick=1),
    yaxis=dict(title="Volume (toneladas)"),
    hovermode="x unified",
    legend=dict(
        title="Estado",
        orientation="v",
        yanchor="top",
        y=1,
        xanchor="left",
        x=1.01
    ),
    margin=dict(l=50, r=150, t=60, b=50),
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
)

st.plotly_chart(fig_volume, use_container_width=True)

# Opção alternativa: Gráfico de linhas
st.subheader("📈 Evolução do Volume por Estado (Linhas)")

fig_linhas = px.line(
    df_volume_ano,
    x="ano",
    y="volume",
    color="estado",
    title="Evolução Temporal da Produção por Estado",
    labels={"ano": "Ano", "volume": "Volume (toneladas)", "estado": "Estado"},
    markers=True,
    color_discrete_sequence=px.colors.qualitative.Set3
)

fig_linhas.update_layout(
    xaxis=dict(tickmode='linear', dtick=1),
    yaxis=dict(title="Volume (toneladas)"),
    hovermode="x unified",
    legend=dict(
        title="Estado",
        orientation="v",
        yanchor="top",
        y=1,
        xanchor="left",
        x=1.01
    ),
    margin=dict(l=50, r=150, t=60, b=50),
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
)

st.plotly_chart(fig_linhas, use_container_width=True)

