import streamlit as st
import psycopg2
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import plotly_express as px
import os
from dotenv import load_dotenv
import pycountry


load_dotenv()
DB_URL = os.getenv("DB_URL")

def get_dataframe(query):
    conn = psycopg2.connect(DB_URL)
    df = pd.read_sql(query, conn)
    conn.close()
    return df

st.set_page_config(page_title="Dashboard do Café")
st.title("☕ Dashboard do Café")

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

# cores personalizadas
coffee_scale = [
    [0.00, "#f8f1e3"],  
    [0.30, "#d9a673"],
    [0.60, "#8b4513"],
    [1.00, "#3e2723"],
]

# decide automatico se usa log ou nao
vol_min = float(df["volume"].replace(0, np.nan).min() or 0)
vol_max = float(df["volume"].max() or 0)
use_log = vol_max > 0 and (vol_max / max(vol_min, 1)) >= 20

df["volume_plot"] = df["volume"]
colorbar_title = "volume"
tickmode = None
tickvals = None
ticktext = None

if use_log:
    # log(1+x) para evitar -inf em zeros
    df["volume_plot"] = np.log1p(df["volume"]).astype(float)
    colorbar_title = "volume (log)"

    
    if vol_max > 1:
        raw_ticks = np.geomspace(1, vol_max, 5) 
        tickvals = np.log1p(raw_ticks)
        ticktext = [f"{int(t):,}".replace(",", ".") for t in raw_ticks]
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

#hover legível
fig.update_traces(
    hovertemplate="<b>%{location}</b><br>" +
                  "Volume: %{customdata} t<extra></extra>",
    customdata=[f"{int(v):,}".replace(",", ".") for v in df["volume"]]
)

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


# Mapa Mundi de Exportação de Café do Brasil
st.header("🌍 Exportação de Café do Brasil por País")

conn = psycopg2.connect(DB_URL)
query_exportacao = """
SELECT p.descricao AS pais, COALESCE(SUM(d.volume), 0) AS volume
FROM pais p
LEFT JOIN destino d ON p.idpais = d.idpais
GROUP BY p.descricao
ORDER BY volume DESC;
"""
df_exportacao = pd.read_sql(query_exportacao, conn)
conn.close()

# mapeamento manual de países p/ plotly
country_mapping = {
    "E.U.A.": "United States of America",
    "ALEMANHA": "Germany",
    "ITALIA": "Italy",
    "BELGICA": "Belgium",
    "JAPAO": "Japan",
    "PAISES BAIXOS (HOLANDA)": "Netherlands",
    "TURQUIA": "Turkey",
    "ESPANHA": "Spain",
    "RUSSIAN FEDERATION": "Russia",
    "COREIA DO SUL (REPUBL.)": "South Korea",
    "FRANCA": "France",
    "REINO UNIDO": "United Kingdom",
    "SUECIA": "Sweden",
    "ESLOVENIA": "Slovenia",
    "GRECIA": "Greece",
    "VIETNAM": "Vietnam",
}


def translate_country_name(name):
    # tenta mapeamento manual
    if name in country_mapping:
        return country_mapping[name]

    # se não encontrar tentar pycountry
    try:
        country = pycountry.countries.get(name=name)
        if country:
            return country.name
        
        for country in pycountry.countries:
            if name.lower() in country.name.lower() or (hasattr(country, 'common_name') and name.lower() in country.common_name.lower()):
                return country.name
        # tenta correspondência aproximada
        import difflib
        matches = difflib.get_close_matches(name, [c.name for c in pycountry.countries], n=1, cutoff=0.6)
        if matches:
            return matches[0]
        return name
    except:
        return name

df_exportacao["pais_traduzido"] = df_exportacao["pais"].apply(translate_country_name)

coffee_scale_world = [
    [0.00, "#f8f1e3"],  
    [0.30, "#d9a673"],
    [0.60, "#8b4513"],
    [1.00, "#3e2723"],
]


vol_min_world = float(df_exportacao["volume"].replace(0, np.nan).min() or 0)
vol_max_world = float(df_exportacao["volume"].max() or 0)
use_log_world = vol_max_world > 0 and (vol_max_world / max(vol_min_world, 1)) >= 20

df_exportacao["volume_plot"] = df_exportacao["volume"]
colorbar_title_world = "volume"
tickmode_world = None
tickvals_world = None
ticktext_world = None

if use_log_world:
    df_exportacao["volume_plot"] = np.log1p(df_exportacao["volume"]).astype(float)
    colorbar_title_world = "volume (log)"
    if vol_max_world > 1:
        raw_ticks_world = np.geomspace(1, vol_max_world, 5)
        tickvals_world = np.log1p(raw_ticks_world)
        ticktext_world = [f"{int(t):,}".replace(",", ".") for t in raw_ticks_world]
        tickmode_world = "array"

fig_world = px.choropleth(
    df_exportacao,
    locations="pais_traduzido",
    locationmode="country names",
    color="volume_plot",
    color_continuous_scale=coffee_scale_world,
    title="Exportação de Café do Brasil por País",
)

fig_world.update_geos(fitbounds="locations", visible=False)

fig_world.update_traces(
    hovertemplate="<b>%{location}</b><br>" +
                  "Volume: %{customdata} t<extra></extra>",
    customdata=[f"{int(v):,}".replace(",", ".") for v in df_exportacao["volume"]]
)

fig_world.update_layout(
    coloraxis_colorbar=dict(
        title=colorbar_title_world,
        thickness=16,
        tickmode=tickmode_world,
        tickvals=tickvals_world,
        ticktext=ticktext_world,
    ),
    margin=dict(l=0, r=0, t=60, b=0),
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
)

st.plotly_chart(fig_world, use_container_width=True)

# Evolução do Preço Médio no Varejo
st.header("📊 Evolução do Preço Médio no Varejo")

conn = psycopg2.connect(DB_URL)
query_preco_varejo = """
SELECT ano, mes, valor
FROM precovarejo
WHERE valor IS NOT NULL
ORDER BY ano, mes;
"""
df_preco_varejo = pd.read_sql(query_preco_varejo, conn)
conn.close()

# coluna de data x
df_preco_varejo["data"] = pd.to_datetime(df_preco_varejo["ano"].astype(str) + "-" + df_preco_varejo["mes"].astype(str).str.zfill(2) + "-01")

fig_preco = px.line(
    df_preco_varejo,
    x="data",
    y="valor",
    title="Evolução do Preço Médio do Café no Varejo",
    labels={"data": "Data", "valor": "Preço Médio (R$)"},
    markers=False,
    line_shape="linear",
)

fig_preco.update_layout(
    xaxis_title="Data",
    yaxis_title="Preço Médio (R$)",
    hovermode="x unified",
    margin=dict(l=50, r=50, t=60, b=50),
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
)

st.plotly_chart(fig_preco, use_container_width=True)

# Produção Total do País ao Longo dos Anos
st.header("📊 Produção Total do País ao Longo dos Anos")

conn = psycopg2.connect(DB_URL)
query_total_ano = """
SELECT ano, SUM(volume) AS volume_total
FROM producao
GROUP BY ano
ORDER BY ano;
"""
df_total_ano = pd.read_sql(query_total_ano, conn)
conn.close()

fig_total_ano = px.line(
    df_total_ano,
    x="ano",
    y="volume_total",
    title="Produção Total de Café no Brasil por Ano",
    labels={"ano": "Ano", "volume_total": "Volume Total (toneladas)"},
    markers=True,
    line_shape="linear",
)

fig_total_ano.update_layout(
    xaxis=dict(tickmode='linear', dtick=1),
    yaxis_title="Volume Total (toneladas)",
    hovermode="x unified",
    margin=dict(l=50, r=50, t=60, b=50),
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
)

st.plotly_chart(fig_total_ano, use_container_width=True)

# Correlação entre Preço de Varejo e Volume de Produção
st.header("🔗 Correlação entre Preço de Varejo e Volume de Produção")

conn = psycopg2.connect(DB_URL)
query_prod_ano = """
SELECT ano, SUM(volume) AS volume_total
FROM producao
GROUP BY ano
ORDER BY ano;
"""
df_prod_ano = pd.read_sql(query_prod_ano, conn)

query_preco_ano = """
SELECT ano, AVG(valor) AS preco_medio
FROM precovarejo
GROUP BY ano
ORDER BY ano;
"""
df_preco_ano = pd.read_sql(query_preco_ano, conn)
conn.close()

df_corr = pd.merge(df_prod_ano, df_preco_ano, on="ano", how="inner")

fig_corr = px.scatter(
    df_corr,
    x="volume_total",
    y="preco_medio",
    trendline="ols",
    title="Correlação entre Volume de Produção e Preço Médio no Varejo",
    labels={"volume_total": "Volume Produzido (toneladas)", "preco_medio": "Preço Médio (R$)"},
)

fig_corr.update_layout(
    xaxis_title="Volume Produzido (toneladas)",
    yaxis_title="Preço Médio (R$)",
    margin=dict(l=50, r=50, t=60, b=50),
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
)

st.plotly_chart(fig_corr, use_container_width=True)

# Produção por Tipo e Espécie
st.header("📊 Produção por Tipo e Espécie")

conn = psycopg2.connect(DB_URL)
query_prod_tipo_especie = """
SELECT t.nome AS tipo,
       e.nome AS especie,
       COALESCE(SUM(p.volume), 0) AS volume
FROM producao p
JOIN tipo t ON p.idTipo = t.idTipo
JOIN especie e ON p.idEspecie = e.idEspecie
GROUP BY t.nome, e.nome
ORDER BY t.nome, volume DESC;
"""
df_prod_tipo = pd.read_sql(query_prod_tipo_especie, conn)
conn.close()

fig_prod_bar = px.bar(
    df_prod_tipo,
    x="volume",
    y="especie",
    color="tipo",
    orientation="h",
    title="Volume de Produção por Espécie e Tipo",
    labels={"volume": "Volume (toneladas)", "especie": "Espécie", "tipo": "Tipo"},
    color_discrete_sequence=px.colors.qualitative.Set3
)

fig_prod_bar.update_layout(
    xaxis_title="Volume (toneladas)",
    yaxis_title="Espécie",
    margin=dict(l=150, r=50, t=60, b=50),
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
)

st.plotly_chart(fig_prod_bar, use_container_width=True)

# Comparativo Volume x Receita de Exportação (Dispersão)
# st.header("🔁 Comparativo: Volume x Receita de Exportação por País")

# conn = psycopg2.connect(DB_URL)
# query_exp_comp = """
# SELECT p.descricao AS pais,
#        COALESCE(SUM(d.volume), 0) AS volume,
#        COALESCE(SUM(e.receita), 0) AS receita
# FROM pais p
# LEFT JOIN destino d ON p.idpais = d.idpais
# LEFT JOIN exportacao e ON e.ano = d.ano AND e.idEspecie = d.idEspecie
# GROUP BY p.descricao
# ORDER BY receita DESC;
# """
# df_exp_comp = pd.read_sql(query_exp_comp, conn)
# conn.close()

# # Garantir tipos numéricos
# df_exp_comp["volume"] = pd.to_numeric(df_exp_comp["volume"], errors="coerce").fillna(0)
# df_exp_comp["receita"] = pd.to_numeric(df_exp_comp["receita"], errors="coerce").fillna(0)

# # Gráfico de dispersão
# fig_exp_scatter = px.scatter(
#     df_exp_comp,
#     x="volume",
#     y="receita",
#     size="volume",
#     size_max=60,
#     hover_name="pais",
#     color="receita",
#     color_continuous_scale="Viridis",
#     title="Comparativo Volume x Receita de Exportação (cada ponto = país)",
#     labels={"volume": "Volume Exportado (toneladas)", "receita": "Receita (US$)"},
# )

# fig_exp_scatter.update_layout(
#     xaxis_title="Volume Exportado (toneladas)",
#     yaxis_title="Receita (US$)",
#     margin=dict(l=50, r=50, t=60, b=50),
#     paper_bgcolor="rgba(0,0,0,0)",
#     plot_bgcolor="rgba(0,0,0,0)",
#     coloraxis_colorbar=dict(title="Receita (US$)", thickness=16),
# )

# st.plotly_chart(fig_exp_scatter, use_container_width=True)

# Evolução da Receita das Exportações
st.header("📈 Evolução da Receita das Exportações")

conn = psycopg2.connect(DB_URL)
query_receita_exportacao = """
SELECT ano, SUM(receita) AS receita_total
FROM exportacao
GROUP BY ano
ORDER BY ano;
"""
df_receita_exportacao = pd.read_sql(query_receita_exportacao, conn)
conn.close()

fig_receita = px.line(
    df_receita_exportacao,
    x="ano",
    y="receita_total",
    title="Evolução da Receita das Exportações de Café",
    labels={"ano": "Ano", "receita_total": "Receita Total (US$)"},
    markers=True,
    line_shape="linear",
)

fig_receita.update_layout(
    xaxis=dict(tickmode='linear', dtick=1),
    yaxis_title="Receita Total (US$)",
    hovermode="x unified",
    margin=dict(l=50, r=50, t=60, b=50),
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
)

st.plotly_chart(fig_receita, use_container_width=True)
