import streamlit as st
import pandas as pd
import re
import matplotlib.pyplot as plt

# Función para extraer el site_id del site_name
def extraer_site_id(site_name):
    match = re.search(r"SF(\d+)[A-Z]+\d+", site_name)
    return match.group(1) if match else None

# Función para cargar bases de datos
@st.cache_data
def cargar_datos(archivo, tipo):
    try:
        df = pd.read_excel(archivo, engine="openpyxl")
        
        if tipo == "base":
            if "site_id" not in df.columns or "region" not in df.columns:
                st.error("⚠️ El archivo base no contiene las columnas necesarias ('site_id', 'region').")
                return None
            df["site_id"] = df["site_id"].astype(str)

        elif tipo == "afectados":
            if "site_name" not in df.columns:
                st.error("⚠️ El archivo no contiene la columna 'site_name'.")
                return None
            df["site_name"] = df["site_name"].astype(str).str.replace('"', '')
            df["site_id"] = df["site_name"].apply(extraer_site_id)
            df["site_id"] = df["site_id"].astype(str)

        elif tipo == "rectificadores":
            if "site_id" not in df.columns:
                st.error("⚠️ El archivo de rectificadores no contiene 'site_id'.")
                return None
            df["site_id"] = df["site_id"].astype(str)

        elif tipo == "nodos_caidos":
            if "site_name" not in df.columns:
                st.error("⚠️ El archivo de nodos caídos no contiene 'site_name'.")
                return None
            df["site_name"] = df["site_name"].astype(str).str.replace('"', '')
            df["site_id"] = df["site_name"].apply(extraer_site_id)
            df["site_id"] = df["site_id"].astype(str)    

        return df
    except Exception as e:
        st.error(f"❌ Error al leer el archivo ({tipo}): {e}")
        return None

# Función para buscar sitios manualmente
def buscar_sites_por_id(df, site_ids):
    site_ids = [site.strip() for site in re.split(r"[,\s]+", site_ids) if site.strip()]
    df_result = df[df["site_id"].isin(site_ids)]
    return df_result.sort_values(by="region") if "region" in df_result.columns else df_result

# Configurar la aplicación
st.set_page_config(page_title="Análisis de Energía", layout="wide")

# Inicializar session_state para almacenar los DataFrames
if "df_base" not in st.session_state:
    st.session_state.df_base = None
if "df_afectados" not in st.session_state:
    st.session_state.df_afectados = None
if "df_rectificadores" not in st.session_state:
    st.session_state.df_rectificadores = None
if "df_nodos_caidos" not in st.session_state:
    st.session_state.df_nodos_caidos = None

# Menú de navegación
menu = st.sidebar.radio("🔍 Navegación", ["Análisis de Masivas", "Búsqueda Manual", "Rectificadores"])


# -------------------------- VISTA: Análisis de Masivas --------------------------
if menu == "Análisis de Masivas":
    import io
    from datetime import datetime
    import matplotlib.ticker as ticker  # Importar para eje Y en enteros

    # Archivos en columnas
    st.markdown("<h2 style='text-align: center;'>📊 Análisis de Sitios Afectados por Energía ⚡</h2>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        archivo_base = st.file_uploader("📂 Sube el archivo base LCR_Regiones (Excel)", type="xlsx", key="base_masiva")
    with col2:
        archivo_afectados_1 = st.file_uploader("📂 Sube el primer archivo con sitios afectados (Excel)", type="xlsx")
    with col3:
        archivo_afectados_2 = st.file_uploader("📂 Sube el segundo archivo con sitios afectados (Excel)", type="xlsx")

    # Archivo de nodos caídos centrado
    st.markdown("<h2 style='text-align: center;'>📊 Análisis de Estaciones Base Caídas por Energía ⚡</h2>", unsafe_allow_html=True)
    col_empty1, col_center, col_empty2 = st.columns([1, 2, 1])
    with col_center:
        archivo_nodos_caidos = st.file_uploader("📂 Sube el archivo de nodos caídos (Excel)", type="xlsx")
    
    col_fecha, col_hora = st.columns([1, 1])
    with col_fecha:
        fecha_afectacion = st.date_input("📅 Fecha de afectación", key="fecha_afectacion")
    with col_hora:
        hora_afectacion = st.text_input("⏰ Hora de afectación (HH:MM)", value="00:00", key="hora_afectacion")

    st.markdown(
        f"""
        <div style="background-color:#254441; padding:8px 15px; border-radius:6px;">
            <span style="font-size:15px;">🕒 <strong>Afectación reportada el:</strong> {fecha_afectacion} a las {hora_afectacion}</span>
        </div>
        <br/>
        """,
        unsafe_allow_html=True
    )

    # Cargar archivos
    if archivo_base:
        st.session_state.df_base = cargar_datos(archivo_base, "base")
    if archivo_afectados_1:
        st.session_state.df_afectados = cargar_datos(archivo_afectados_1, "afectados")
    if archivo_afectados_2:
        df_afectados_2 = cargar_datos(archivo_afectados_2, "afectados")
        if df_afectados_2 is not None:
            st.session_state.df_afectados = pd.concat([st.session_state.df_afectados, df_afectados_2], ignore_index=True)
    if archivo_nodos_caidos:
        st.session_state.df_nodos_caidos = cargar_datos(archivo_nodos_caidos, "nodos_caidos")

    if st.session_state.df_base is not None and st.session_state.df_afectados is not None:
        st.success("✅ Archivos cargados correctamente.")
        df_merged = st.session_state.df_afectados.merge(st.session_state.df_base, on="site_id", how="left")

        if df_merged["region"].isna().all():
            st.warning("⚠️ No se encontraron coincidencias en la base de datos.")
        else:
            df_merged = df_merged.sort_values(by="region")
            df_merged_unique = df_merged.drop_duplicates(subset="site_id")
            resumen = df_merged_unique.groupby("region").size().reset_index(name="cantidad_sitios")

            st.write("### 📌 Resumen de sitios afectados por región")
            st.dataframe(resumen)

            # Visualización de gráficos
            st.markdown("<h4 style='text-align: center;'>📈 Visualización de Sitios Afectados</h4>", unsafe_allow_html=True)
            colores = ['#4c72b0', '#55a868', '#c44e52', '#8172b2', '#ccb974', '#64b5cd']            

            col_empty, col_center, _ = st.columns([1, 2, 1])
            with col_center:
                st.markdown("##### 📊 Distribución por Región")
                fig_bar, ax_bar = plt.subplots(figsize=(4, 3))
                ax_bar.bar(resumen["region"], resumen["cantidad_sitios"], color=colores[:len(resumen)])
                ax_bar.set_ylabel("Cantidad", fontsize=9)
                ax_bar.set_xlabel("Región", fontsize=9)
                ax_bar.tick_params(axis='x', labelrotation=45, labelsize=8)
                ax_bar.tick_params(axis='y', labelsize=8)
                ax_bar.yaxis.set_major_locator(ticker.MaxNLocator(integer=True))  # Solo enteros
                fig_bar.tight_layout()
                st.pyplot(fig_bar)            

            st.write("### 📋 Información Detallada de Sitios Afectados")

            # ✅ Eliminar columna 'site_name_y' si existe
            if "site_name_y" in df_merged.columns:
                df_merged = df_merged.drop(columns=["site_name_y"])

            st.dataframe(df_merged)

    # Análisis nodos caídos
    if st.session_state.df_nodos_caidos is not None and st.session_state.df_base is not None:
        st.success("✅ Archivo de nodos caídos cargado correctamente.")
        df_nodos_merged = st.session_state.df_nodos_caidos.merge(
            st.session_state.df_base[["site_id", "region", "priority"]],
            on="site_id", how="left"
        )

        if df_nodos_merged["region"].isna().all():
            st.warning("⚠️ No se encontraron coincidencias en la base de datos.")
        else:
            df_nodos_merged_unique = df_nodos_merged.drop_duplicates(subset="site_id")
            resumen_nodos = df_nodos_merged_unique.groupby("region").size().reset_index(name="cantidad_nodos")

            st.write("### 🔴 Resumen de Estaciones Base Caídas por Energía")
            st.dataframe(resumen_nodos)

            col1, col2 = st.columns(2)
            with col1:
                st.markdown("##### 📉 Distribución por Región")
                fig_bar2, ax_bar2 = plt.subplots(figsize=(3.5, 2.8))
                ax_bar2.bar(resumen_nodos["region"], resumen_nodos["cantidad_nodos"], color=colores[:len(resumen_nodos)])
                ax_bar2.set_ylabel("Cantidad", fontsize=8)
                ax_bar2.set_xlabel("Región", fontsize=8)
                ax_bar2.tick_params(axis='x', labelrotation=45, labelsize=7)
                ax_bar2.tick_params(axis='y', labelsize=7)
                ax_bar2.yaxis.set_major_locator(ticker.MaxNLocator(integer=True))  # ✅ Solo enteros
                fig_bar2.tight_layout()
                st.pyplot(fig_bar2)

            with col2:
                st.markdown("##### 📉 Distribución por Región")
                fig_pie2, ax_pie2 = plt.subplots(figsize=(3.2, 3.2))
                wedges2, texts2, autotexts2 = ax_pie2.pie(
                    resumen_nodos["cantidad_nodos"],
                    labels=resumen_nodos["region"],
                    autopct='%1.1f%%',
                    startangle=90,
                    colors=colores[:len(resumen_nodos)],
                    textprops={'fontsize': 7},
                    labeldistance=1.1,
                    pctdistance=0.7
                )
                for text in texts2:
                    text.set_fontsize(7)
                for autotext in autotexts2:
                    autotext.set_fontsize(7)
                ax_pie2.axis('equal')
                fig_pie2.tight_layout()
                st.pyplot(fig_pie2)

            st.write("### 📋 Información Detallada de Estaciones Caídas")
            df_nodos_merged_sorted = df_nodos_merged.sort_values(by=["region", "priority"])
            st.dataframe(df_nodos_merged_sorted)

            # Exportar resumen completo
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                resumen.to_excel(writer, sheet_name='Resumen', index=False)
                df_merged.to_excel(writer, sheet_name='Sitios Detallados', index=False)
                resumen_nodos.to_excel(writer, sheet_name='Nodos Caídos', index=False)
                df_nodos_merged_sorted.to_excel(writer, sheet_name='Nodos Detallados', index=False)

                workbook = writer.book
                sheet1 = writer.sheets['Resumen']
                sheet2 = writer.sheets['Nodos Caídos']

                # Gráficos sitios afectados
                imgdata1 = io.BytesIO()
                fig_bar.savefig(imgdata1, format='png', bbox_inches='tight')
                sheet1.insert_image('G2', 'bar_chart_afectados.png', {'image_data': imgdata1})                

                # Gráficos nodos caídos
                imgdata3 = io.BytesIO()
                fig_bar2.savefig(imgdata3, format='png', bbox_inches='tight')
                sheet2.insert_image('G2', 'bar_chart_nodos.png', {'image_data': imgdata3})

                imgdata4 = io.BytesIO()
                fig_pie2.savefig(imgdata4, format='png', bbox_inches='tight')
                sheet2.insert_image('G20', 'pie_chart_nodos.png', {'image_data': imgdata4})

            now = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            st.download_button(
                label="📅 Descargar Reporte Completo en Excel",
                data=output.getvalue(),
                file_name=f"reporte_masiva_{now}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

# -------------------------- VISTA: Búsqueda Manual --------------------------
elif menu == "Búsqueda Manual":
    st.title("🔍 Buscar Sitios Manualmente")

    # Subir archivo base
    archivo_base = st.file_uploader("📂 Sube el archivo base LCR_Regiones (Excel)", type="xlsx", key="base_busqueda")
    colores = ['#4c72b0', '#55a868', '#c44e52', '#8172b2', '#ccb974', '#64b5cd']

    if archivo_base:
        st.session_state.df_base = cargar_datos(archivo_base, "base")

    # Si ya hay base cargada
    if st.session_state.df_base is not None:
        st.success("✅ Base de datos cargada correctamente.")

        # Entrada de IDs
        site_ids_input = st.text_input("✍️ Ingresa los Site IDs separados por coma o espacio:", key="busqueda_manual_input")

        # Botón de búsqueda
        if st.button("🔎 Buscar"):
            if site_ids_input:
                df_result = buscar_sites_por_id(st.session_state.df_base, site_ids_input)
                st.session_state.resultado_busqueda_manual = df_result  # ✅ Guardar en session_state
            else:
                st.error("⚠️ Ingresa al menos un Site ID.")

        # Mostrar resultado si existe
        if "resultado_busqueda_manual" in st.session_state:
            df_result = st.session_state.resultado_busqueda_manual

            # ✅ Eliminar filas completamente vacías y resetear índice
            df_result = df_result.dropna(how='all').reset_index(drop=True)

            if not df_result.empty:
                st.write("### 📋 Información de Sitios Encontrados")
                st.dataframe(
                    df_result,
                    use_container_width=True,
                    hide_index=True
                )

                # Gráfico si existe columna 'region'
                if "region" in df_result.columns:
                    resumen_busqueda = df_result.groupby("region").size().reset_index(name="cantidad")

                    col_empty, col_center, _ = st.columns([1, 2, 1])
                    with col_center:
                        st.markdown("##### 📊 Distribución por Región")
                        fig_busq, ax_busq = plt.subplots(figsize=(2.5, 2.0))

                        # ✅ Ajustar grosor de barra si solo hay una
                        bar_width = 0.3 if len(resumen_busqueda) == 1 else 0.8

                        ax_busq.bar(
                            resumen_busqueda["region"],
                            resumen_busqueda["cantidad"],
                            color=colores[:len(resumen_busqueda)],
                            width=bar_width
                        )
                        ax_busq.set_ylabel("Cantidad de sitios", fontsize=5)
                        ax_busq.set_xlabel("Región", fontsize=5)
                        ax_busq.tick_params(axis='x', labelrotation=45, labelsize=4)
                        ax_busq.tick_params(axis='y', labelsize=4)

                        # ✅ Eje Y como enteros
                        ax_busq.yaxis.get_major_locator().set_params(integer=True)

                        fig_busq.tight_layout()
                        st.pyplot(fig_busq)
            else:
                st.warning("⚠️ No se encontraron sitios con esos IDs.")


# -------------------------- VISTA: Rectificadores --------------------------
elif menu == "Rectificadores":
    st.title("🔌 Verificar Respaldo de Sitios (Rectificadores)")

    # Subida del archivo de rectificadores
    archivo_rectificadores = st.file_uploader("📂 Sube el archivo de Inventario_rectificadores (Excel)", type="xlsx")

    if archivo_rectificadores:
        st.session_state.df_rectificadores = cargar_datos(archivo_rectificadores, "rectificadores")

    # Si hay datos cargados
    if st.session_state.df_rectificadores is not None:
        st.success("✅ Base de rectificadores cargada correctamente.")

        # Entrada de Site IDs
        site_ids_input = st.text_input("✍️ Ingresa los Site IDs separados por coma o espacio:", key="rectificadores_input")

        # Botón para buscar
        if st.button("🔎 Buscar"):
            if site_ids_input:
                df_result = buscar_sites_por_id(st.session_state.df_rectificadores, site_ids_input)
                st.session_state.resultado_rectificadores = df_result
            else:
                st.error("⚠️ Ingresa al menos un Site ID.")

        # Mostrar resultado si ya existe
        if "resultado_rectificadores" in st.session_state:
            df_result = st.session_state.resultado_rectificadores
            if not df_result.empty:
                st.write("### 🔋 Información de Respaldo de Sitios")

                # ✅ Limpiar índice
                df_result = df_result.reset_index(drop=True)

                # ✅ Mostrar tabla sin índice visual
                st.dataframe(
                    df_result,
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.warning("⚠️ No se encontraron sitios con esos IDs.")