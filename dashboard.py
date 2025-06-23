import streamlit as st
import psycopg2
from psycopg2 import Error
from os import environ
from dotenv import load_dotenv
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns  # Importando seaborn para estilo moderno

# Carregar variáveis de ambiente
load_dotenv()

# Configurar estilo moderno com seaborn
sns.set_style("whitegrid")  # Estilo Seaborn com grade branca
plt.rcParams['figure.facecolor'] = '#f0f2f6'  # Fundo claro e moderno
plt.rcParams['axes.facecolor'] = '#ffffff'    # Fundo branco para os eixos
plt.rcParams['axes.edgecolor'] = '#333333'    # Bordas escuras
plt.rcParams['axes.labelcolor'] = '#333333'   # Rótulos escuros
plt.rcParams['text.color'] = '#333333'        # Texto escuro
plt.rcParams['xtick.color'] = '#333333'       # Cores dos ticks
plt.rcParams['ytick.color'] = '#333333'

# Conexão com o banco de dados
def get_db_connection():
    try:
        conn = psycopg2.connect(environ.get("DB_URL"))
        return conn
    except Error as e:
        st.error(f"Erro ao conectar ao banco de dados: {e}")
        return None

# Função para carregar dados de todas as tabelas
def load_data(conn):
    try:
        # Destino (Exportações por País)
        query_destino = """
        SELECT d.ano, d.mes, p.descricao, d.volume
        FROM Destino d
        JOIN Pais p ON d.idPais = p.idPais
        ORDER BY d.ano, d.mes;
        """
        df_destino = pd.read_sql_query(query_destino, conn)

        # ConsumoInterno
        query_consumo = """
        SELECT ano, volume
        FROM ConsumoInterno
        ORDER BY ano;
        """
        df_consumo = pd.read_sql_query(query_consumo, conn)

        # Exportacao
        query_exportacao = """
        SELECT e.ano, t.nome AS tipo, es.nome AS especie, e.receita, e.volume
        FROM Exportacao e
        JOIN Tipo t ON e.idTipo = t.idTipo
        JOIN Especie es ON e.idEspecie = es.idEspecie
        ORDER BY e.ano;
        """
        df_exportacao = pd.read_sql_query(query_exportacao, conn)

        # PrecoVarejo
        query_preco = """
        SELECT ano, mes, valor
        FROM PrecoVarejo
        ORDER BY ano, mes;
        """
        df_preco = pd.read_sql_query(query_preco, conn)

        # Producao
        query_producao = """
        SELECT p.ano, e.descricao AS estado, p.idRegiao, t.nome AS tipo, es.nome AS especie, p.area, p.volume
        FROM Producao p
        JOIN Estado e ON p.idEstado = e.idEstado
        JOIN Tipo t ON p.idTipo = t.idTipo
        JOIN Especie es ON p.idEspecie = es.idEspecie
        ORDER BY p.ano;
        """
        df_producao = pd.read_sql_query(query_producao, conn)

        return df_destino, df_consumo, df_exportacao, df_preco, df_producao
    except Error as e:
        st.error(f"Erro ao carregar dados: {e}")
        return None, None, None, None, None

# Configuração da página
st.title("Dashboard de Exportações, Produção e Consumo de Café")
st.write("Análise dos dados de café processados até 23 de junho de 2025.")

# Conectar ao banco e carregar dados
conn = get_db_connection()
if conn:
    df_destino, df_consumo, df_exportacao, df_preco, df_producao = load_data(conn)
    if all(df is not None for df in [df_destino, df_consumo, df_exportacao, df_preco, df_producao]) and not any(df.empty for df in [df_destino, df_consumo, df_exportacao, df_preco, df_producao]):

        # Layout em duas colunas
        col1, col2 = st.columns(2)

        # # Gráfico 1: Total de Exportações por Ano (Destino) - Coluna 1
        # with col1:
        #     st.subheader("Exportações por Ano")
        #     export_ano = df_destino.groupby('ano')['volume'].sum()
        #     fig1, ax1 = plt.subplots(figsize=(5, 3))  # Tamanho reduzido
        #     ax1.bar(export_ano.index, export_ano.values, color='#4CAF50')  # Verde moderno
        #     ax1.set_xlabel('Ano')
        #     ax1.set_ylabel('Volume (sacas de 60 kg)')
        #     ax1.tick_params(axis='x', rotation=45)
        #     ax1.grid(True, linestyle='--', alpha=0.7)
        #     st.pyplot(fig1)

        # Gráfico 2: Consumo Interno por Ano (ConsumoInterno) - Coluna 2
        with col2:
            st.subheader("Consumo Interno por Ano")
            fig2, ax2 = plt.subplots(figsize=(5, 3))  # Tamanho reduzido
            ax2.plot(df_consumo['ano'], df_consumo['volume'], marker='o', color='#2196F3', linewidth=2)  # Azul moderno
            ax2.set_xlabel('Ano')
            ax2.set_ylabel('Consumo Per Capita (kg/habitante/ano)')
            ax2.grid(True, linestyle='--', alpha=0.7)
            st.pyplot(fig2)

        # Nova linha de colunas
        col3, col4 = st.columns(2)

        # Gráfico 3: Exportação por Tipo e Espécie (Exportacao) - Coluna 1
        with col3:
            st.subheader("Exportação por Tipo e Espécie")
            export_pivot = df_exportacao.pivot_table(values='volume', index='tipo', columns='especie', aggfunc='sum', fill_value=0)
            fig3, ax3 = plt.subplots(figsize=(5, 3))  # Tamanho reduzido
            export_pivot.plot(kind='bar', ax=ax3, color=['#FF9800', '#F44336'])  # Laranja e vermelho moderno
            ax3.set_xlabel('Tipo de Café')
            ax3.set_ylabel('Volume (sacas de 60 kg)')
            ax3.tick_params(axis='x', rotation=45)
            ax3.grid(True, linestyle='--', alpha=0.7)
            st.pyplot(fig3)

        # Gráfico 4: Preço de Varejo por Ano (PrecoVarejo) - Coluna 2
        with col4:
            st.subheader("Preço de Varejo por Ano")
            preco_ano = df_preco.groupby('ano')['valor'].mean()
            fig4, ax4 = plt.subplots(figsize=(5, 3))  # Tamanho reduzido
            ax4.plot(preco_ano.index, preco_ano.values, marker='o', color='#9C27B0', linewidth=2)  # Roxo moderno
            ax4.set_xlabel('Ano')
            ax4.set_ylabel('Preço Médio (R$/kg)')
            ax4.grid(True, linestyle='--', alpha=0.7)
            st.pyplot(fig4)

        # Gráfico 5: Produção por Estado (Producao) - Linha completa
        st.subheader("Produção por Estado")
        prod_estado = df_producao.groupby('estado')['volume'].sum()
        fig5, ax5 = plt.subplots(figsize=(10, 4))  # Tamanho ajustado para caber mais estados
        ax5.bar(prod_estado.index, prod_estado.values, color='#673AB7')  # Roxo escuro moderno
        ax5.set_xlabel('Estado')
        ax5.set_ylabel('Volume Total (sacas de 60 kg)')
        ax5.tick_params(axis='x', rotation=90)  # Rotação para melhor legibilidade
        ax5.grid(True, linestyle='--', alpha=0.7)
        st.pyplot(fig5)

    else:
        st.warning("Nenhum dado disponível para exibir os gráficos.")
    conn.close()