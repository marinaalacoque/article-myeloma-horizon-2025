import streamlit as st
import pandas as pd
import json
import plotly.graph_objects as go
import numpy as np
from scipy.stats import linregress


# DataFrame com dados extraídos (para informações gerais e data de início)
df = pd.read_csv("./ctg-studies-filtered.csv")

# Converter datas para anos (formato 'YYYY-MM-DD')
df["startYear"] = df["studyFirstSubmitDate"].str[:4].astype(int)
# Se endDate não existir, usamos lastUpdateSubmitDate para determinar o fim da atividade
df["endYear"] = df["endDate"].str[:4].fillna(df["lastUpdateSubmitDate"].str[:4]).astype(int)

# Cria uma coluna com a lista de anos em que o estudo esteve ativo
df["years"] = df.apply(lambda x: list(range(x["startYear"], x["endYear"] + 1)), axis=1)

# Expandir: cada linha terá um único ano (coluna "year") – usado para o gráfico de estudos ativos
df_expanded = df.explode("years").rename(columns={"years": "year"})

# Remover estudos com status indesejados (opcional)
# df_expanded = df_expanded[~df_expanded["overallStatus"].isin(["WITHDRAWN", "SUSPENDED", "UNKNOWN"])]

# --- INTERFACE STREAMLIT ---

st.title("Dashboard de Estudos Clínicos")

st.markdown(
    """
    Utilize os filtros na barra lateral para selecionar:
    
    - **Overall Status** e **Fases** (afetam ambos os gráficos);
    - **Intervalo de Anos Ativos** (para o gráfico de Estudos Ativos);
    - **Intervalo de Anos de Início** (para o gráfico de Estudos Iniciados);
    - **Com ou Sem Resultados** (para filtrar os estudos por envio de resultados).
    """
)

# Sidebar de filtros
st.sidebar.header("Filtros")

# Filtro para overallStatus
unique_status = sorted(df_expanded["overallStatus"].unique())
default_status = [status for status in unique_status if status not in ["WITHDRAWN", "SUSPENDED", "UNKNOWN"]]
selected_status = st.sidebar.multiselect(
    "Selecione os Overall Status:",
    unique_status,
    default=default_status
)

# Filtro para phases
unique_phases = sorted(df_expanded["phases"].unique())
selected_phases = st.sidebar.multiselect(
    "Selecione as Fases:",
    unique_phases,
    default=unique_phases
)

# Filtro para Resultados
selected_results_option = st.sidebar.radio(
    "Selecione se deseja filtrar por estudos com ou sem resultados:",
    ("Todos", "Com Resultados", "Sem Resultados")
)

# Slider para intervalo de anos ativos (usado no gráfico 1)
min_active_year = int(df_expanded["year"].min())
max_active_year = int(df_expanded["year"].max())
active_year_range = st.sidebar.slider(
    "Selecione o intervalo de Anos Ativos:",
    min_active_year,
    max_active_year,
    (2014, 2024)
)

# Slider para intervalo de anos de início (usado no gráfico 2)
min_start_year = int(df["startYear"].min())
max_start_year = int(df["startYear"].max())
start_year_range = st.sidebar.slider(
    "Selecione o intervalo de Anos de Início:",
    min_start_year,
    max_start_year,
    (min_start_year, max_start_year)
)

# --- GRÁFICO 1: ESTUDOS CLÍNICOS POR FASE (ATIVOS) ---

# Filtrar dados para o gráfico 1 (usando o intervalo de anos ativos)
filtered_active = df_expanded[
    (df_expanded["overallStatus"].isin(selected_status)) &
    (df_expanded["phases"].isin(selected_phases)) &
    (df_expanded["year"] >= active_year_range[0]) &
    (df_expanded["year"] <= active_year_range[1])
]

# Aplicar filtro de resultados, se necessário
if selected_results_option == "Com Resultados":
    filtered_active = filtered_active[filtered_active["sendResult"] == True]
elif selected_results_option == "Sem Resultados":
    filtered_active = filtered_active[filtered_active["sendResult"] == False]

# Agregar contagem de estudos por ano e por fase
df_counts = filtered_active.groupby(["year", "phases"]).size().unstack(fill_value=0)

fig1 = go.Figure()
colors = {
    "PHASE1": "blue",
    "PHASE2": "red",
    "PHASE3": "green",
    "PHASE1, PHASE2": "purple",
    "PHASE2, PHASE3": "orange",
    "EARLY_PHASE1": "gray"
}

for phase in df_counts.columns:
    fig1.add_trace(go.Bar(
        x=df_counts.index,
        y=df_counts[phase],
        name=phase,
        marker_color=colors.get(phase, "black")
    ))

# Calcular e adicionar a curva de tendência linear para o gráfico 1 (se houver dados suficientes)
total_by_year = df_counts.sum(axis=1)
if len(total_by_year) > 1:
    log_years = np.log(total_by_year.index)
    if np.any(np.isnan(log_years) | np.isinf(log_years)):
        raise ValueError("Os anos contêm valores inválidos para logaritmo.")
    slope, intercept, r, p, se = linregress(total_by_year.index, total_by_year)
    slope_apc,intercept_apc,r_apc,p_apc,se_apc= linregress(total_by_year.index, np.log(total_by_year))
    y_trend = slope * total_by_year.index + intercept
    fig1.add_trace(go.Scatter(
        x=total_by_year.index,
        y=y_trend,
        mode="lines",
        name="Tendência Linear",
        line=dict(color="red", dash="dot")
    ))
    st.markdown(f"**Taxa de aumento de estudos ativos: {slope:.2f} estudos/ano - r: {r:.2f} - p: {p:.4f} - se: {se:.2f}**")
    APC = (np.exp(slope_apc) - 1) * 100
    st.markdown(f"** APC{APC:.2f}-slope_apc: {slope_apc:.2f} - r: {r_apc:.2f} - p: {p_apc:.4f} - se: {se_apc:.2f}**")
else:
    st.markdown("**Não há dados suficientes para calcular a taxa de aumento dos estudos ativos.**")

fig1.update_layout(
    title="Estudos Clínicos por Fase (Ativos)",
    xaxis_title="Ano",
    yaxis_title="Número de Estudos",
    barmode="stack",
    template="plotly_white",
    legend_title="Fases"
)

st.plotly_chart(fig1, use_container_width=True)

# --- GRÁFICO 2: ESTUDOS INICIADOS POR ANO ---

st.markdown("---")
st.markdown("### Estudos Iniciados por Ano")

# Filtrar dados para o gráfico 2 (usando o intervalo de anos de início)
filtered_starts = df[
    (df["overallStatus"].isin(selected_status)) &
    (df["phases"].isin(selected_phases)) &
    (df["startYear"] >= start_year_range[0]) &
    (df["startYear"] <= start_year_range[1])
]

# Aplicar filtro de resultados, se necessário
if selected_results_option == "Com Resultados":
    filtered_starts = filtered_starts[filtered_starts["sendResult"] == True]
elif selected_results_option == "Sem Resultados":
    filtered_starts = filtered_starts[filtered_starts["sendResult"] == False]

# Agregar contagem de estudos iniciados por ano e por fase
df_starts = filtered_starts.groupby(["startYear", "phases"]).size().unstack(fill_value=0)

fig2 = go.Figure()
for phase in df_starts.columns:
    fig2.add_trace(go.Bar(
        x=df_starts.index,
        y=df_starts[phase],
        name=phase,
        marker_color=colors.get(phase, "black")
    ))

# Calcular e adicionar a tendência linear para o gráfico 2 (para o total de estudos iniciados)
total_starts_by_year = df_starts.sum(axis=1)
if len(total_starts_by_year) > 1:
    slope_start, intercept_start, *_ = linregress(total_starts_by_year.index, total_starts_by_year.values)
    y_trend_start = slope_start * total_starts_by_year.index + intercept_start
    fig2.add_trace(go.Scatter(
        x=total_starts_by_year.index,
        y=y_trend_start,
        mode="lines",
        name="Tendência Linear",
        line=dict(color="red", dash="dot")
    ))
    st.markdown(f"**Taxa de aumento de estudos iniciados: {slope_start:.2f} estudos/ano**")
else:
    st.markdown("**Não há dados suficientes para calcular a taxa de aumento dos estudos iniciados.**")

fig2.update_layout(
    title="Estudos Iniciados por Ano",
    xaxis_title="Ano de Início",
    yaxis_title="Número de Estudos Iniciados",
    barmode="stack",
    template="plotly_white",
    legend_title="Fases"
)

st.plotly_chart(fig2, use_container_width=True)
