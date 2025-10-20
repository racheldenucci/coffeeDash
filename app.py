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

# discrete sequence personalizado
coffee_discrete_sequence = [
    "#3e2723",
    "#654321",
    "#2f1b14",
    "#f8f1e3",
    "#e6d7c3",
    "#d9a673",
    "#b8860b",
    "#a0522d",
    "#8b4513",
    "#1a0f0a",
    "#daa520",
    "#cd853f",
]

@st.cache_data
def get_dataframe(query, params=None):
    conn = psycopg2.connect(DB_URL)
    df = pd.read_sql(query, conn, params=params)
    conn.close()
    return df

st.set_page_config(page_title="Dashboard do Café", layout="wide", page_icon="coffee")
st.title(":coffee: Dashboard do Café")

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.header(":seedling: Produção")
        # Obter anos disponíveis
    anos_df = get_dataframe("SELECT DISTINCT ano FROM producao ORDER BY ano DESC")
    anos = anos_df["ano"].tolist()

    # Filtro de ano
    anos_selecionados = st.multiselect("Selecione o(s) Ano(s)", anos, default=anos, key="ano_producao")

    if not anos_selecionados:
        st.warning("Selecione pelo menos um ano.")
        anos_selecionados = anos

col1, col2 = st.columns(2)
#-------------- PRODUÇÃO ----------------------
with col1: # mapa produção por estado

    query = """
    SELECT e.descricao AS estado, COALESCE(SUM(p.volume), 0) AS volume
    FROM estado e
    LEFT JOIN producao p ON e.idestado = p.idestado AND p.ano = ANY(%s)
    GROUP BY e.descricao
    ORDER BY e.descricao;
    """
    df = get_dataframe(query, params=(anos_selecionados,))

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
        colorbar_title = "volume"

        
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
        title=f"Volume Produzido",
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

with col2: # produção total por ano
    
   
    query_total_ano = """
    SELECT ano, SUM(volume) AS volume_total
    FROM producao
    GROUP BY ano
    ORDER BY ano;
    """
    df_total_ano = get_dataframe(query_total_ano)

    fig_total_ano = px.line(
        df_total_ano,
        x="ano",
        y="volume_total",
        title="Produção Total por Ano",
        labels={"ano": "Ano", "volume_total": "Volume Total Produzido (toneladas)"},
        markers=True,
        line_shape="linear",
    )

    fig_total_ano.update_traces(line_color="#654321")

    fig_total_ano.update_layout(
        xaxis=dict(tickmode='auto', dtick=1),
        yaxis_title="Volume Total (toneladas)",
        hovermode="x unified",
        margin=dict(l=50, r=50, t=60, b=50),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )

    st.plotly_chart(fig_total_ano, use_container_width=True)

with col1: # volume produzido por estado e ano
    
    query_volume_ano = """
    SELECT p.ano, e.descricao AS estado, SUM(p.volume) AS volume
    FROM producao p
    JOIN estado e ON p.idestado = e.idestado
    GROUP BY p.ano, e.descricao
    ORDER BY p.ano, e.descricao;
    """
    df_volume_ano = get_dataframe(query_volume_ano)

    fig_volume = px.bar(
        df_volume_ano,
        x="ano",
        y="volume",
        color="estado",
        title="Volume Produzido por Ano",
        labels={"ano": "Ano", "volume": "Volume (toneladas)", "estado": "Estado"},
        barmode="stack",
        color_discrete_sequence=coffee_discrete_sequence
    )

    fig_volume.update_layout(
        xaxis=dict(tickmode='auto', dtick=1),
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
    
with col2: # produção por Espécie
    
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
    df_prod_tipo = get_dataframe(query_prod_tipo_especie)

    fig_prod_bar = px.bar(
        df_prod_tipo,
        x="volume",
        y="especie",
        color="tipo",
        orientation="h",
        title="Volume Total Produzido por Espécie",
        labels={"volume": "Volume (toneladas)", "especie": "Espécie", "tipo": "Tipo"},
        color_discrete_sequence=coffee_discrete_sequence
    )

    fig_prod_bar.update_layout(
        xaxis_title="Volume (toneladas)",
        yaxis_title="Espécie",
        margin=dict(l=150, r=50, t=60, b=50),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )

    st.plotly_chart(fig_prod_bar, use_container_width=True)

#-------------- EXPORTAÇÃO ----------------------
co1, co2, co3, co4 = st.columns(4)
with co1:
    st.header(":earth_americas: Exportação")
     # Obter anos disponíveis para exportação
    anos_export_df = get_dataframe("SELECT DISTINCT ano FROM destino ORDER BY ano DESC")
    anos_export = anos_export_df["ano"].tolist()

    # Filtro de ano para exportação
    anos_export_selecionados = st.multiselect("Selecione o(s) Ano(s)", anos_export, default=anos_export, key="ano_exportacao")

    if not anos_export_selecionados:
        st.warning("Selecione pelo menos um ano.")
        anos_export_selecionados = anos_export

        
col1, col2 = st.columns(2)
with col1: # mapa de exportação    

    query_exportacao = """
    SELECT p.descricao AS pais, COALESCE(SUM(d.volume), 0) AS volume
    FROM pais p
    LEFT JOIN destino d ON p.idpais = d.idpais AND d.ano = ANY(%s)
    GROUP BY p.descricao
    ORDER BY volume DESC;
    """
    df_exportacao = get_dataframe(query_exportacao, params=(anos_export_selecionados,))

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
        colorbar_title_world = "volume"
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
        title="Exportação de Café do Brasil por Destino",
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

with col2: # evolução receita exportações

    query_receita_exportacao = """
    SELECT ano, SUM(receita) AS receita_total
    FROM exportacao
    GROUP BY ano
    ORDER BY ano;
    """
    df_receita_exportacao = get_dataframe(query_receita_exportacao)

    fig_receita = px.line(
        df_receita_exportacao,
        x="ano",
        y="receita_total",
        title="Receita Total das Exportações de Café",
        labels={"ano": "Ano", "receita_total": "Receita Total (US$)"},
        markers=True,
        line_shape="linear",
    )

    fig_receita.update_traces(line_color="#654321")

    fig_receita.update_layout(
        xaxis=dict(tickmode='auto', dtick=1),
        yaxis_title="Receita Total (US$)",
        hovermode="x unified",
        margin=dict(l=50, r=50, t=60, b=50),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )

    st.plotly_chart(fig_receita, use_container_width=True)


#-------------- CONSUMO INTERNO ----------------------
with col1: #evolução preço médio varejo
    st.header("")
    st.header(":coffee: Consumo Interno")

    query_preco_varejo = """
    SELECT ano, mes, valor
    FROM precovarejo
    WHERE valor IS NOT NULL
    ORDER BY ano, mes;
    """
    df_preco_varejo = get_dataframe(query_preco_varejo)

    # coluna de data x
    df_preco_varejo["data"] = pd.to_datetime(df_preco_varejo["ano"].astype(str) + "-" + df_preco_varejo["mes"].astype(str).str.zfill(2) + "-01")

    fig_preco = px.line(
        df_preco_varejo,
        x="data",
        y="valor",
        title="Preço Médio do Café no Varejo",
        labels={"data": "Data", "valor": "Preço Médio (R$)"},
        markers=False,
        line_shape="linear",
    )

    fig_preco.update_traces(line_color="#654321")

    fig_preco.update_layout(
        xaxis_title="Data",
        yaxis_title="Preço Médio (R$)",
        hovermode="x unified",
        margin=dict(l=50, r=50, t=60, b=50),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )

    st.plotly_chart(fig_preco, use_container_width=True)

with col2: # correlação preço varejo x volume produção

    st.header("")
    st.header("")

    query_prod_ano = """
    SELECT ano, SUM(volume) AS volume_total
    FROM producao
    GROUP BY ano
    ORDER BY ano;
    """
    df_prod_ano = get_dataframe(query_prod_ano)

    query_preco_ano = """
    SELECT ano, AVG(valor) AS preco_medio
    FROM precovarejo
    GROUP BY ano
    ORDER BY ano;
    """
    df_preco_ano = get_dataframe(query_preco_ano)

    df_corr = pd.merge(df_prod_ano, df_preco_ano, on="ano", how="inner")

    fig_corr = px.scatter(
        df_corr,
        x="volume_total",
        y="preco_medio",
        trendline="ols",
        title="Correlação Volume Produzido x Preço Médio no Varejo",
        labels={"volume_total": "Volume Produzido (toneladas)", "preco_medio": "Preço Médio (R$)"},
    )

    fig_corr.update_traces(marker_color="#654321")

    fig_corr.update_layout(
        xaxis_title="Volume Produzido (toneladas)",
        yaxis_title="Preço Médio (R$)",
        margin=dict(l=50, r=50, t=60, b=50),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )

    st.plotly_chart(fig_corr, use_container_width=True)

with col1: # evolução consumo interno

    query_consumo_interno = """
    SELECT ano, volume
    FROM consumoInterno
    WHERE ANO > 1985
    ORDER BY ano;
    """
    df_consumo_interno = get_dataframe(query_consumo_interno)

    fig_consumo = px.line(
        df_consumo_interno,
        x="ano",
        y="volume",
        title="Consumo Interno de Café",
        labels={"ano": "Ano", "volume": "Consumo Per Capita (kg/habitante/ano)"},
        markers=True,
        line_shape="linear",
    )

    fig_consumo.update_traces(line_color="#654321")

    fig_consumo.update_layout(
        xaxis=dict(tickmode='auto', dtick=1),
        yaxis_title="Consumo Per Capita (kg/habitante/ano)",
        hovermode="x unified",
        margin=dict(l=50, r=50, t=60, b=50),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )

    st.plotly_chart(fig_consumo, use_container_width=True)

with col2: # preço médio x consumo interno

    query_preco_consumo = """
    SELECT ci.ano, ci.volume AS consumo_per_capita, pv.valor AS preco_medio
    FROM consumoInterno ci
    JOIN (
        SELECT ano, AVG(valor) AS valor
        FROM precovarejo
        GROUP BY ano
    ) pv ON ci.ano = pv.ano
    WHERE ci.ano > 1985
    ORDER BY ci.ano;
    """
    df_preco_consumo = get_dataframe(query_preco_consumo)

    fig_preco_consumo = px.scatter(
        df_preco_consumo,
        x="consumo_per_capita",
        y="preco_medio",
        trendline="ols",
        title="Correlação Preço Médio x Consumo Interno",
        labels={"consumo_per_capita": "Consumo Per Capita (kg/habitante/ano)", "preco_medio": "Preço Médio (R$)"},
    )

    fig_preco_consumo.update_traces(marker_color="#654321")

    fig_preco_consumo.update_layout(
        xaxis_title="Consumo Per Capita (kg/habitante/ano)",
        yaxis_title="Preço Médio (R$)",
        margin=dict(l=50, r=50, t=60, b=50),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )

    st.plotly_chart(fig_preco_consumo, use_container_width=True)
