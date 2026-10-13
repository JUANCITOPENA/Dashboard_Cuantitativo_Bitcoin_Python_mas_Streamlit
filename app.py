import streamlit as st
import requests
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
import os

# ==========================================
# CONFIGURACIÓN DE PÁGINA
# ==========================================
st.set_page_config(
    page_title="Dashboard Cuantitativo Crypto",
    page_icon="📈",
    layout="wide"
)

# ==========================================
# CSS CORREGIDO (Menos espacio SIN romper la flecha de reapertura)
# ==========================================
st.markdown("""
    <style>
        /* Reduce espacio superior del contenedor principal */
        .block-container {
            padding-top: 1.5rem !important;
            padding-bottom: 0rem !important;
        }

        /* Reduce espacio superior de la barra lateral */
        [data-testid="stSidebarUserContent"] {
            padding-top: 1.5rem !important;
        }

        /* Cabecera transparente y compacta (conserva la flecha '>' para reabrir el menú) */
        header[data-testid="stHeader"] {
            background-color: transparent !important;
            height: 2.2rem !important;
            z-index: 100 !important;
        }

        /* Asegura que el botón de desplegar barra lateral sea visible */
        [data-testid="stSidebarCollapsedControl"] {
            display: block !important;
            color: #2c3e50 !important;
        }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# FUNCIÓN: OBTENER EL TOP 10 DE CRIPTOS MÁS CARAS
# ==========================================
@st.cache_data(ttl=600)  # Se actualiza cada 10 minutos
def obtener_top_10_mas_caras():
    url = "https://api.binance.com/api/v3/ticker/price"
    try:
        data = requests.get(url, timeout=10).json()
        
        # Filtramos solo pares en USDT y descartamos tokens derivados/apalancados
        excluir = ["UPUSDT", "DOWNUSDT", "BULLUSDT", "BEARUSDT"]
        filtrados = [
            {"symbol": item["symbol"], "price": float(item["price"])}
            for item in data
            if item["symbol"].endswith("USDT") and not any(e in item["symbol"] for e in excluir)
        ]
        
        df_top = pd.DataFrame(filtrados)
        # Ordenar por precio más alto a más bajo
        df_top = df_top.sort_values(by="price", ascending=False).head(10).reset_index(drop=True)
        return df_top
    except Exception:
        # Respaldo en caso de fallo de red
        return pd.DataFrame({
            "symbol": ["BTCUSDT", "WBTCUSDT", "PAXGUSDT", "YFIUSDT", "ETHUSDT"],
            "price": [90000.0, 90000.0, 2700.0, 6000.0, 2600.0]
        })

df_top10 = obtener_top_10_mas_caras()
lista_top10_simbolos = df_top10["symbol"].tolist()

# ==========================================
# BARRA LATERAL (CONTROLES)
# ==========================================
st.sidebar.header("⚙️ Parámetros de Mercado")

simbolo = st.sidebar.selectbox(
    "🏆 Top 10 Criptos Más Caras (Binance):",
    options=lista_top10_simbolos,
    index=0
)

dias = st.sidebar.slider(
    "Horizonte temporal (días)",
    min_value=30,
    max_value=365,
    value=90,
    step=5
)

with st.sidebar.expander("📋 Ver Ranking Top 10 Precios"):
    tabla_mostrar = df_top10.copy()
    tabla_mostrar["price"] = tabla_mostrar["price"].apply(lambda x: f"${x:,.2f}")
    tabla_mostrar.columns = ["Activo", "Precio (USDT)"]
    st.dataframe(tabla_mostrar, hide_index=True, use_container_width=True)

# ==========================================
# EXTRACCIÓN HISTÓRICA (VELAS 1D)
# ==========================================
@st.cache_data(ttl=300)
def cargar_datos(symbol: str, limit: int):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1d&limit={limit}"
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    raw = response.json()
    
    cols = ["OpenTime", "Open", "High", "Low", "Close", "Volume"]
    df = pd.DataFrame(raw).iloc[:, :6]
    df.columns = cols
    
    df["Fecha"] = pd.to_datetime(df["OpenTime"], unit="ms")
    df[cols[1:]] = df[cols[1:]].astype(float)
    
    # Indicadores Cuantitativos
    df["Var_Dia_%"] = ((df["Close"] - df["Open"]) / df["Open"]) * 100
    df["SMA_20"] = df["Close"].rolling(20).mean()
    df["SMA_50"] = df["Close"].rolling(50).mean()
    df["Retorno_Acum_%"] = ((df["Close"] / df["Close"].iloc[0]) - 1) * 100
    
    # RSI 14
    delta = df["Close"].diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    df["RSI"] = 100 - (100 / (1 + gain / (loss + 1e-9)))
    
    return df

with st.spinner(f"Descargando historial de {simbolo}..."):
    try:
        df = cargar_datos(simbolo, dias)
    except Exception as e:
        st.error(f"Error al obtener datos: {e}")
        st.stop()

# ==========================================
# KPIS
# ==========================================
p_act = df["Close"].iloc[-1]
ret_tot = df["Retorno_Acum_%"].iloc[-1]
rsi_act = df["RSI"].iloc[-1]
min_val = df["Low"].min()
max_val = df["High"].max()

# ==========================================
# ENCABEZADO CON FOTO DEL AUTOR A LA DERECHA
# ==========================================
col_titulo, col_foto = st.columns([4.8, 1.2])

with col_titulo:
    st.title(f"📊 Dashboard Cuantitativo: {simbolo}")
    st.caption(f"Análisis de los últimos {dias} días | Cotización en vivo al {datetime.now().strftime('%d/%m/%Y')}")

with col_foto:
    # Ruta relativa al archivo (funciona local y en la nube)
    directorio_base = os.path.dirname(os.path.abspath(__file__))
    ruta_foto = os.path.join(directorio_base, "IMG", "JUANCITOPENA.png")
    
    if os.path.exists(ruta_foto):
        st.image(ruta_foto, width=85, caption="Juancito Peña")
    elif os.path.exists("IMG/JUANCITOPENA.png"):
        st.image("IMG/JUANCITOPENA.png", width=85, caption="Juancito Peña")

# ==========================================
# TARJETAS DE KPIS
# ==========================================
col1, col2, col3, col4 = st.columns(4)
col1.metric("Precio Actual", f"${p_act:,.2f}")
col2.metric("Retorno del Periodo", f"{ret_tot:+.2f}%", delta=f"{ret_tot:+.2f}%")
col3.metric(
    "RSI (14D)",
    f"{rsi_act:.1f}",
    delta="Sobrecompra (>70)" if rsi_act > 70 else ("Sobreventa (<30)" if rsi_act < 30 else "Zona Neutral"),
    delta_color="inverse" if rsi_act > 70 else "normal"
)
col4.metric("Rango (Mín - Máx)", f"${min_val:,.2f} - ${max_val:,.2f}")

st.markdown("---")

# ==========================================
# DASHBOARD GRÁFICO (4 PANELES)
# ==========================================
fig, ax = plt.subplots(2, 2, figsize=(18, 10))
fig.patch.set_facecolor("#f8f9fa")

# Panel 1: Tendencia y Medias
ax[0, 0].fill_between(df["Fecha"], df["Low"], df["High"], color="#3498db", alpha=0.15, label="Rango Diario (H-L)")
ax[0, 0].plot(df["Fecha"], df["Close"], label="Precio Cierre", color="#2c3e50", lw=2.2)
ax[0, 0].plot(df["Fecha"], df["SMA_20"], label="SMA 20 (Corto plazo)", color="#e67e22", ls="--")
ax[0, 0].plot(df["Fecha"], df["SMA_50"], label="SMA 50 (Tendencia base)", color="#27ae60", ls="--")
ax[0, 0].set_title(f"1. Estructura de Tendencia ({dias}D): Precio vs Medias Móviles", fontweight="bold")

# Panel 2: Retorno Acumulado %
ax[0, 1].fill_between(df["Fecha"], df["Retorno_Acum_%"], 0, where=(df["Retorno_Acum_%"] >= 0), color="#2ecc71", alpha=0.3, label="Ganancia")
ax[0, 1].fill_between(df["Fecha"], df["Retorno_Acum_%"], 0, where=(df["Retorno_Acum_%"] < 0), color="#e74c3c", alpha=0.3, label="Pérdida")
ax[0, 1].plot(df["Fecha"], df["Retorno_Acum_%"], color="#2c3e50", lw=2)
ax[0, 1].axhline(0, color="gray", ls=":", lw=1.2)
ax[0, 1].set_title(f"2. Rendimiento Acumulado del Periodo ({ret_tot:+.2f}%)", fontweight="bold")

# Panel 3: Flujo de Volumen Direccional
colores_vol = ["#2ecc71" if c >= o else "#e74c3c" for c, o in zip(df["Close"], df["Open"])]
ax[1, 0].bar(df["Fecha"], df["Volume"], color=colores_vol, width=0.8, alpha=0.85)
ax[1, 0].plot(df["Fecha"], df["Volume"].rolling(14).mean(), color="#8e44ad", lw=2, label="Media Vol 14D")
ax[1, 0].set_title("3. Flujo de Volumen: Acumulación (Verde) vs Distribución (Rojo)", fontweight="bold")

# Panel 4: Momentum RSI 14
ax[1, 1].plot(df["Fecha"], df["RSI"], color="#8e44ad", lw=2, label="RSI 14")
ax[1, 1].axhline(70, color="#c0392b", ls="--", alpha=0.8, label="Sobrecompra (>70)")
ax[1, 1].axhline(30, color="#27ae60", ls="--", alpha=0.8, label="Sobreventa (<30)")
ax[1, 1].fill_between(df["Fecha"], 70, 30, color="gray", alpha=0.08)
ax[1, 1].set(ylim=(10, 90), title=f"4. Momentum de Mercado (RSI Actual: {rsi_act:.1f})")

# Estilos globales
for a in ax.flat:
    a.set_facecolor("#ffffff")
    a.grid(alpha=0.25, ls="--")
    a.legend(loc="upper left", fontsize=8, framealpha=0.8)
    a.xaxis.set_major_formatter(mdates.DateFormatter('%d/%b'))
    a.tick_params(axis="x", rotation=30)

plt.tight_layout()
st.pyplot(fig, use_container_width=True)

# ==========================================
# TABLA DE REGISTROS CON FORMATOS CONDICIONALES
# ==========================================
with st.expander("🔍 Explorar Datos y Cálculos con Formato Condicional"):
    # Funciones de estilo por condición
    def colorear_rendimiento(val):
        if pd.isna(val):
            return ""
        if val > 0:
            return "background-color: #d4edda; color: #155724; font-weight: bold;"  # Verde suave
        elif val < 0:
            return "background-color: #f8d7da; color: #721c24; font-weight: bold;"  # Rojo suave
        return "background-color: #fff3cd; color: #856404; font-weight: bold;"      # Amarillo suave

    def colorear_rsi(val):
        if pd.isna(val):
            return ""
        if val >= 70:
            return "background-color: #f8d7da; color: #721c24; font-weight: bold;"  # Sobrecompra (Rojo Alerta)
        elif val <= 30:
            return "background-color: #d4edda; color: #155724; font-weight: bold;"  # Sobreventa (Verde Entrada)
        return "background-color: #fff3cd; color: #856404;"                         # Neutral (Amarillo)

    # Preparar columnas
    columnas_tabla = [
        "Fecha", "Open", "High", "Low", "Close",
        "Var_Dia_%", "Retorno_Acum_%", "Volume", "SMA_20", "SMA_50", "RSI"
    ]
    df_tabla = df[columnas_tabla].sort_values(by="Fecha", ascending=False).copy()

    # Aplicación directa y encadenada de estilos
    styler = df_tabla.style
    if hasattr(styler, "map"):
        styler = styler.map(colorear_rendimiento, subset=["Var_Dia_%", "Retorno_Acum_%"])
        styler = styler.map(colorear_rsi, subset=["RSI"])
    else:
        styler = styler.applymap(colorear_rendimiento, subset=["Var_Dia_%", "Retorno_Acum_%"])
        styler = styler.applymap(colorear_rsi, subset=["RSI"])

    # Formateo numérico y de fechas
    tabla_estilizada = styler.format({
        "Fecha": lambda x: x.strftime("%d/%m/%Y"),
        "Open": "${:,.2f}",
        "High": "${:,.2f}",
        "Low": "${:,.2f}",
        "Close": "${:,.2f}",
        "Var_Dia_%": "{:+.2f}%",
        "Retorno_Acum_%": "{:+.2f}%",
        "Volume": "{:,.2f}",
        "SMA_20": lambda x: f"${x:,.2f}" if pd.notna(x) else "-",
        "SMA_50": lambda x: f"${x:,.2f}" if pd.notna(x) else "-",
        "RSI": lambda x: f"{x:.1f}" if pd.notna(x) else "-"
    })

    st.dataframe(tabla_estilizada, use_container_width=True)