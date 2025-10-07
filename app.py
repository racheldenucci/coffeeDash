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
st.title("☕ Dashboard de Dados do Café")

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


# # 1. Produção por Estado
# st.header("📈 Produção por Estado")
# df_prod = get_dataframe("""
#     SELECT e.descricao AS estado, SUM(p.volume) AS volumetotal
#     FROM producao p
#     JOIN estado e ON p.idEstado = e.idEstado
#     GROUP BY e.descricao
#     ORDER BY volumetotal DESC
# """)
# st.bar_chart(df_prod.set_index("estado").sort_values("volumetotal"))

# # 2. Exportação por Espécie
# # st.header("💵 Receita de Exportação por Espécie")
# # df_exp = get_dataframe("""
# #     SELECT es.descricao AS especie, SUM(e.receita) AS receitatotal
# #     FROM exportacao e
# #     JOIN especie es ON e.idEspecie = es.idEspecie
# #     GROUP BY es.descricao
# #     ORDER BY receitatotal DESC
# # """)
# # st.bar_chart(df_exp.set_index("especie"))

# # 3. Destinos de Exportação
# st.header("🌍 Exportações por País de Destino")
# df_dest = get_dataframe("""
#     SELECT pa.descricao AS pais, SUM(d.volume) AS volumetotal
#     FROM destino d
#     JOIN pais pa ON d.idPais = pa.idPais
#     GROUP BY pa.descricao
#     ORDER BY volumetotal DESC
# """)
# st.bar_chart(df_dest.set_index("pais"))

# # 4. Evolução do Preço Médio no Varejo
# st.header("🛒 Preço Médio no Varejo (R$/kg)")
# df_preco = get_dataframe("""
#     SELECT ano, mes, valor
#     FROM precovarejo
#     ORDER BY ano, mes
# """)
# df_preco['data'] = pd.to_datetime(df_preco['ano'].astype(str) + '-' + df_preco['mes'].astype(str), format='%Y-%m')
# df_preco.set_index("data", inplace=True)
# st.line_chart(df_preco['valor'])

# # 5. Consumo Interno por Tipo
# st.header("☕ Consumo Interno por Tipo de Café")
# df_cons = get_dataframe("""
#     SELECT t.descricao AS tipo, SUM(c.volume) AS consumototal
#     FROM consumointerno c
#     JOIN tipo t ON c.tipo = t.idTipo
#     GROUP BY t.descricao
# """)
# st.bar_chart(df_cons.set_index("tipo"))
