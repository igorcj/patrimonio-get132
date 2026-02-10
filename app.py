import streamlit as st
import psycopg2
import pandas as pd
from PIL import Image
import io
from datetime import datetime

st.set_page_config(page_title="Patrimônio GET 132", page_icon="⚜️", layout="wide")

# --- CONEXÃO ---
def get_db_connection():
    try:
        return psycopg2.connect(
            host=st.secrets["host"], port=st.secrets["port"],
            database=st.secrets["database"], user=st.secrets["user"],
            password=st.secrets["password"], connect_timeout=10
        )
    except Exception as e:
        st.error(f"Erro de Conexão: {e}")
        return None

# --- FUNÇÕES SQL ---
def limpar_reservas_antigas():
    conn = get_db_connection()
    if conn:
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM reservas WHERE data_fim < CURRENT_DATE")
            conn.commit()
            cur.close()
            conn.close()
        except: pass

@st.dialog("Detalhes do Equipamento", width="large")
def modal_detalhes(item):
    st.write(f"### {item['nome']} (#{item['codigo']})")
    st.image(bytes(item['foto_blob']) if item['foto_blob'] else "https://via.placeholder.com/300")
    st.write(f"**Ramo:** {item['ramo']}")
    st.write(f"**Descrição:** {item['descricao']}")
    
    st.divider()
    tab1, tab2, tab3 = st.tabs(["📅 Reservar", "📋 Ver Reservas", "⚙️ Gerenciar"])
    
    with tab1:
        with st.form(f"res_{item['codigo']}", clear_on_submit=True):
            quem = st.text_input("Responsável")
            d_ini = st.date_input("Início", min_value=datetime.now())
            d_fim = st.date_input("Fim", min_value=d_ini)
            if st.form_submit_button("Confirmar Reserva"):
                if quem:
                    conn = get_db_connection()
                    cur = conn.cursor()
                    cur.execute("SELECT id FROM reservas WHERE item_codigo = %s AND NOT (data_fim < %s OR data_inicio > %s)", (item['codigo'], d_ini, d_fim))
                    if cur.fetchone():
                        st.error("Item ocupado nestas datas!")
                    else:
                        cur.execute("INSERT INTO reservas (item_codigo, usuario, data_inicio, data_fim) VALUES (%s, %s, %s, %s)", (item['codigo'], quem, d_ini, d_fim))
                        conn.commit()
                        st.success("Reserva realizada!")
                    conn.close()

    with tab2:
        conn = get_db_connection()
        if conn:
            query_item = "SELECT usuario, data_inicio, data_fim FROM reservas WHERE item_codigo = %s ORDER BY data_inicio ASC"
            df_item_res = pd.read_sql(query_item, conn, params=(item['codigo'],))
            conn.close()
            if not df_item_res.empty:
                df_item_res.columns = ['Responsável', 'Início', 'Fim']
                st.dataframe(df_item_res, use_container_width=True, hide_index=True)
            else:
                st.info("Nenhuma reserva para este item.")

    with tab3:
        st.warning("Atenção: Esta ação removerá o item e todas as suas reservas.")
        if st.checkbox(f"Confirmar que deseja deletar #{item['codigo']}"):
            if st.button("DELETAR PERMANENTEMENTE"):
                conn = get_db_connection()
                cur = conn.cursor()
                cur.execute("DELETE FROM reservas WHERE item_codigo = %s", (item['codigo'],))
                cur.execute("DELETE FROM itens WHERE codigo = %s", (item['codigo'],))
                conn.commit()
                conn.close()
                st.rerun()

# --- PÁGINA: CATÁLOGO ---
def exibir_catalogo():
    st.title("📦 Catálogo GET 132")
    
    # Filtros Sempre Visíveis no Topo
    c1, c2 = st.columns([2, 3])
    busca = c1.text_input("🔍 Buscar por nome ou código")
    ramos = c2.multiselect("⚜️ Filtrar Ramos", ["Alcatéia", "Escoteiro", "Sênior", "Pioneiro", "Grupo"], default=["Alcatéia", "Escoteiro", "Sênior", "Pioneiro", "Grupo"])

    conn = get_db_connection()
    if conn:
        df = pd.read_sql("SELECT * FROM itens ORDER BY codigo ASC", conn)
        conn.close()

        if not df.empty:
            df = df[df['ramo'].isin(ramos)]
            if busca:
                df = df[df.apply(lambda r: busca.lower() in str(r.values).lower(), axis=1)]

            # Lógica de colunas: 1 por linha no celular (ou telas muito estreitas), 4 no PC
            # O Streamlit ajusta automaticamente o layout, mas st.columns facilita o controle
            num_cols = 1 if st.session_state.get('viewport_width', 1000) < 600 else 4
            cols = st.columns(num_cols)
            
            for i, row in df.reset_index(drop=True).iterrows():
                with cols[i % num_cols]:
                    st.image(bytes(row['foto_blob']) if row['foto_blob'] else "https://via.placeholder.com/300", use_container_width=True)
                    st.write(f"**#{row['codigo']} {row['nome']}**")
                    st.caption(f"Ramo: {row['ramo']}")
                    if st.button("Ver / Reservar", key=f"btn_{row['codigo']}", use_container_width=True):
                        modal_detalhes(row)
                    st.write("") # Espaçador

# --- PÁGINA: AGENDA ---
def exibir_agenda():
    st.title("📅 Agenda de Reservas")
    limpar_reservas_antigas()
    
    conn = get_db_connection()
    if conn:
        df = pd.read_sql("""
            SELECT r.data_inicio, r.data_fim, r.usuario, i.nome, i.codigo 
            FROM reservas r JOIN itens i ON r.item_codigo = i.codigo
            ORDER BY r.data_inicio ASC
        """, conn)
        conn.close()

        if not df.empty:
            hoje = datetime.now().date()
            
            def destacar_hoje(row):
                if row['data_inicio'] <= hoje <= row['data_fim']:
                    return ['background-color: #d1e7dd; color: #0f5132; font-weight: bold'] * len(row)
                return [''] * len(row)

            st.write("Linhas em **verde** indicam equipamentos que estão fora hoje.")
            df_view = df.rename(columns={'data_inicio': 'Início', 'data_fim': 'Fim', 'codigo': 'Cód', 'nome': 'Item', 'usuario': 'Responsável'})
            st.dataframe(df_view.style.apply(destacar_hoje, axis=1), use_container_width=True, hide_index=True)
        else:
            st.info("Nenhuma reserva futura.")

# --- PÁGINA: CADASTRO ---
def exibir_cadastro():
    st.title("➕ Cadastrar Item")
    with st.form("cad_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        cod = col1.text_input("Código")
        nome = col1.text_input("Nome")
        ramo = col2.selectbox("Ramo", ["Alcatéia", "Escoteiro", "Sênior", "Pioneiro", "Grupo"])
        desc = st.text_area("Descrição")
        foto = st.camera_input("Foto")
        if st.form_submit_button("Salvar"):
            if cod and nome and foto:
                img = Image.open(foto)
                w, h = img.size
                d = min(w, h)
                img = img.crop(((w-d)//2, (h-d)//2, (w+d)//2, (h+d)//2)).resize((300,300))
                buf = io.BytesIO()
                img.convert("RGB").save(buf, format="JPEG", quality=50)
                conn = get_db_connection()
                cur = conn.cursor()
                cur.execute("INSERT INTO itens (codigo, nome, descricao, ramo, foto_blob) VALUES (%s, %s, %s, %s, %s)", (cod, nome, desc, ramo, psycopg2.Binary(buf.getvalue())))
                conn.commit()
                conn.close()
                st.success("Salvo!")

# --- MENU LATERAL ---
opcao = st.sidebar.radio("Navegação", ["📦 Catálogo", "📅 Agenda", "➕ Cadastrar"])
if opcao == "📦 Catálogo": exibir_catalogo()
elif opcao == "📅 Agenda": exibir_agenda()
else: exibir_cadastro()