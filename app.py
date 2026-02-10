import streamlit as st
import psycopg2
import pandas as pd
from PIL import Image
import io
from datetime import datetime, date

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

# --- LOGIN ---
if "auth_level" not in st.session_state:
    st.session_state.auth_level = None

if st.session_state.auth_level is None:
    st.title("⚜️ Acesso ao Patrimônio - GET 132")
    senha = st.text_input("Digite a senha de acesso:", type="password")
    if st.button("Entrar"):
        if senha == st.secrets["senha_admin"]:
            st.session_state.auth_level = "admin"
            st.rerun()
        elif senha == st.secrets["senha_membro"]:
            st.session_state.auth_level = "membro"
            st.rerun()
        else:
            st.error("Senha incorreta!")
    st.stop()

# --- LOGOUT (Opcional na barra lateral) ---
if st.sidebar.button("Sair / Trocar Usuário"):
    st.session_state.auth_level = None
    st.rerun()

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

def deletar_reserva_sql(reserva_id):
    conn = get_db_connection()
    if conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM reservas WHERE id = %s", (reserva_id,))
        conn.commit()
        conn.close()
        st.rerun()

# --- MODAL DETALHES ---
@st.dialog("Detalhes do Equipamento", width="large")
def modal_detalhes(item):
    st.write(f"### {item['nome']} (#{item['codigo']})")
    st.image(bytes(item['foto_blob']) if item['foto_blob'] else "https://via.placeholder.com/300")
    st.write(f"**Descrição:** {item['descricao']}")
    
    st.divider()
    # Membros só veem as duas primeiras abas. Admin vê a de Gerenciar.
    tabs_labels = ["📅 Reservar", "📋 Ocupação"]
    if st.session_state.auth_level == "admin":
        tabs_labels.append("⚙️ Gerenciar")
    
    tabs = st.tabs(tabs_labels)
    
    with tabs[0]: # Reservar
        quem = st.text_input("Responsável", key=f"user_input_{item['codigo']}")
        hoje = date.today()
        d_ini = st.date_input("Retirada", value=hoje, min_value=hoje, key=f"start_{item['codigo']}")
        d_fim = st.date_input("Devolução", value=d_ini, min_value=d_ini, key=f"end_{item['codigo']}")
        
        if st.button("Confirmar Reserva", use_container_width=True):
            if quem:
                conn = get_db_connection()
                cur = conn.cursor()
                cur.execute("SELECT id FROM reservas WHERE item_codigo = %s AND NOT (data_fim < %s OR data_inicio > %s)", (item['codigo'], d_ini, d_fim))
                if cur.fetchone():
                    st.error("⚠️ Já reservado neste período!")
                else:
                    cur.execute("INSERT INTO reservas (item_codigo, usuario, data_inicio, data_fim) VALUES (%s, %s, %s, %s)", (item['codigo'], quem, d_ini, d_fim))
                    conn.commit()
                    st.success("✅ Reserva realizada!")
                    st.rerun()
                conn.close()

    with tabs[1]: # Ocupação
        conn = get_db_connection()
        df_res = pd.read_sql("SELECT id, usuario, data_inicio, data_fim FROM reservas WHERE item_codigo = %s ORDER BY data_inicio ASC", conn, params=(item['codigo'],))
        conn.close()
        if not df_res.empty:
            for _, r in df_res.iterrows():
                col_r1, col_r2 = st.columns([3, 1])
                col_r1.write(f"**{r['usuario']}**: {r['data_inicio'].strftime('%d/%m')} - {r['data_fim'].strftime('%d/%m')}")
                if st.session_state.auth_level == "admin":
                    if col_r2.button("Remover", key=f"del_res_{r['id']}"):
                        deletar_reserva_sql(r['id'])
        else:
            st.info("Item livre.")

    if st.session_state.auth_level == "admin":
        with tabs[2]: # Gerenciar
            if st.checkbox("Confirmar exclusão definitiva do ITEM"):
                if st.button("REMOVER ITEM AGORA", type="primary"):
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
    c1, c2 = st.columns([1, 2])
    busca = c1.text_input("🔍 Buscar...")
    ramos = c2.multiselect("⚜️ Ramos", ["Grupo", "Alcatéia", "Escoteiro", "Sênior", "Pioneiro"], default=[])

    conn = get_db_connection()
    if conn:
        df = pd.read_sql("SELECT * FROM itens ORDER BY codigo ASC", conn)
        conn.close()
        if not df.empty:
            df = df[df['ramo'].isin(ramos)]
            if busca:
                df = df[df.apply(lambda r: busca.lower() in str(r.values).lower(), axis=1)]

            cols = st.columns(4)
            for i, row in df.reset_index(drop=True).iterrows():
                with cols[i % 4]:
                    st.image(bytes(row['foto_blob']) if row['foto_blob'] else "https://via.placeholder.com/300", use_container_width=True)
                    st.markdown(f"**#{row['codigo']} {row['nome']}**")
                    st.caption(f"Ramo: {row['ramo']}")
                    if st.button("Ver / Reservar", key=f"btn_cat_{row['codigo']}", use_container_width=True):
                        modal_detalhes(row)

# --- PÁGINA: AGENDA ---
def exibir_agenda():
    st.title("📅 Agenda Geral")
    limpar_reservas_antigas()
    conn = get_db_connection()
    if conn:
        df = pd.read_sql("SELECT r.id, r.data_inicio, r.data_fim, r.usuario, i.nome, i.codigo FROM reservas r JOIN itens i ON r.item_codigo = i.codigo ORDER BY r.data_inicio ASC", conn)
        conn.close()
        if not df.empty:
            hoje = date.today()
            st.write("Linhas em **verde** indicam equipamentos fora hoje.")
            
            # Exibição linha a linha para permitir exclusão na agenda
            for _, row in df.iterrows():
                cor = "#d1e7dd" if row['data_inicio'] <= hoje <= row['data_fim'] else "transparent"
                with st.container():
                    c_ag1, c_ag2, c_ag3 = st.columns([3, 2, 1])
                    with c_ag1:
                        st.markdown(f"<div style='background-color:{cor}; padding:5px; border-radius:5px;'><b>{row['nome']}</b> (#{row['codigo']})<br>{row['usuario']}</div>", unsafe_allow_html=True)
                    with c_ag2:
                        st.write(f"{row['data_inicio'].strftime('%d/%m')} até {row['data_fim'].strftime('%d/%m')}")
                    with c_ag3:
                        if st.session_state.auth_level == "admin":
                            if st.button("Baixa", key=f"ag_del_{row['id']}"):
                                deletar_reserva_sql(row['id'])
                st.divider()
        else:
            st.info("Nenhuma reserva ativa.")

# --- PÁGINA: CADASTRO ---
def exibir_cadastro():
    if st.session_state.auth_level != "admin":
        st.error("Apenas chefes administradores podem cadastrar novos itens.")
        return
    st.title("➕ Cadastrar Item")
    with st.form("cad_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        cod = col1.text_input("Código")
        nome = col1.text_input("Nome")
        ramo = col2.selectbox("Ramo", ["Grupo", "Alcatéia", "Escoteiro", "Sênior", "Pioneiro"])
        desc = st.text_area("Descrição")
        foto_upload = st.file_uploader("Foto", type=['jpg', 'jpeg', 'png'])
        
        if st.form_submit_button("Salvar"):
            if cod and nome and foto_upload:
                img = Image.open(foto_upload)
                d = min(img.size)
                img = img.crop(((img.width-d)//2, (img.height-d)//2, (img.width+d)//2, (img.height+d)//2)).resize((300,300))
                buf = io.BytesIO()
                img.convert("RGB").save(buf, format="JPEG", quality=50)
                conn = get_db_connection()
                cur = conn.cursor()
                cur.execute("INSERT INTO itens (codigo, nome, descricao, ramo, foto_blob) VALUES (%s, %s, %s, %s, %s)", (cod, nome, desc, ramo, psycopg2.Binary(buf.getvalue())))
                conn.commit()
                conn.close()
                st.success("Salvo!")

# --- NAVEGAÇÃO ---
menu_options = ["📦 Catálogo", "📅 Agenda"]
if st.session_state.auth_level == "admin":
    menu_options.append("➕ Cadastrar")

opcao = st.sidebar.radio("Navegação", menu_options)
if opcao == "📦 Catálogo": exibir_catalogo()
elif opcao == "📅 Agenda": exibir_agenda()
else: exibir_cadastro()