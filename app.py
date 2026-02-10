import streamlit as st
import psycopg2
import pandas as pd
from PIL import Image
import io
from datetime import datetime, date

st.set_page_config(page_title="Patrimônio GET 132", page_icon="⚜️", layout="wide")

# --- LISTA PADRÃO DE RAMOS (Grupo primeiro) ---
LISTA_RAMOS = ["Grupo", "Alcatéia", "Escoteiro", "Sênior", "Pioneiro"]

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

# --- CONTROLE DE ACESSO ---
if "auth_level" not in st.session_state:
    st.session_state.auth_level = None
if "user_ramo" not in st.session_state:
    st.session_state.user_ramo = None

if st.session_state.auth_level is None:
    st.title("⚜️ Acesso ao Patrimônio - GET 132")
    user_type = st.selectbox("Selecione seu usuário:", ["Selecionar...", "Admin"] + LISTA_RAMOS[1:])
    senha = st.text_input("Senha:", type="password")
    
    if st.button("Entrar"):
        login_valido = False
        if user_type == "Admin" and senha == st.secrets["senha_admin"]:
            st.session_state.auth_level = "admin"
            st.session_state.user_ramo = "Todos"
            login_valido = True
        elif user_type == "Alcatéia" and senha == st.secrets["senha_lobinho"]:
            st.session_state.auth_level = "membro"
            st.session_state.user_ramo = "Alcatéia"
            login_valido = True
        elif user_type == "Escoteiro" and senha == st.secrets["senha_escoteiro"]:
            st.session_state.auth_level = "membro"
            st.session_state.user_ramo = "Escoteiro"
            login_valido = True
        elif user_type == "Sênior" and senha == st.secrets["senha_senior"]:
            st.session_state.auth_level = "membro"
            st.session_state.user_ramo = "Sênior"
            login_valido = True
        elif user_type == "Pioneiro" and senha == st.secrets["senha_pioneiro"]:
            st.session_state.auth_level = "membro"
            st.session_state.user_ramo = "Pioneiro"
            login_valido = True
        
        if login_valido: st.rerun()
        else: st.error("Senha incorreta!")
    st.stop()

# --- FUNÇÕES SQL ---
def deletar_reserva_sql(reserva_id):
    conn = get_db_connection()
    if conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM reservas WHERE id = %s", (reserva_id,))
        conn.commit(); conn.close()
        st.rerun()

# --- MODAL DETALHES ---
@st.dialog("Detalhes do Equipamento", width="large")
def modal_detalhes(item):
    st.write(f"### {item['nome']} (#{item['codigo']})")
    st.image(bytes(item['foto_blob']) if item['foto_blob'] else "https://via.placeholder.com/300")
    st.markdown(f"**Ramo:** {item['ramo']}")
    st.markdown(f"**Descrição:**\n\n{item['descricao']}")
    st.divider()
    
    tabs_labels = ["📅 Reservar", "📋 Ocupação"]
    if st.session_state.auth_level == "admin": tabs_labels.append("⚙️ Gerenciar")
    tabs = st.tabs(tabs_labels)
    
    with tabs[0]: # Reservar
        quem = st.text_input("Responsável", key=f"user_input_{item['codigo']}")
        hoje = date.today()
        d_ini = st.date_input("Retirada", value=hoje, min_value=hoje, key=f"start_{item['codigo']}")
        d_fim = st.date_input("Devolução", value=d_ini, min_value=d_ini, key=f"end_{item['codigo']}")
        if st.button("Confirmar Reserva", use_container_width=True):
            if quem:
                conn = get_db_connection(); cur = conn.cursor()
                cur.execute("SELECT id FROM reservas WHERE item_codigo = %s AND NOT (data_fim < %s OR data_inicio > %s)", (item['codigo'], d_ini, d_fim))
                if cur.fetchone(): st.error("⚠️ Já reservado!")
                else:
                    cur.execute("INSERT INTO reservas (item_codigo, usuario, data_inicio, data_fim) VALUES (%s, %s, %s, %s)", (item['codigo'], quem, d_ini, d_fim))
                    conn.commit(); st.success("Reserva realizada!"); st.rerun()
                conn.close()

    with tabs[1]: # Ocupação
        conn = get_db_connection()
        df_res = pd.read_sql("SELECT id, usuario, data_inicio, data_fim FROM reservas WHERE item_codigo = %s ORDER BY data_inicio ASC", conn, params=(item['codigo'],))
        conn.close()
        if not df_res.empty:
            for _, r in df_res.iterrows():
                c1, c2 = st.columns([3, 1])
                c1.write(f"**{r['usuario']}**: {r['data_inicio'].strftime('%d/%m')} - {r['data_fim'].strftime('%d/%m')}")
                if st.session_state.auth_level == "admin":
                    if c2.button("Remover", key=f"del_res_{r['id']}"): deletar_reserva_sql(r['id'])
        else: st.info("Item livre.")

    if st.session_state.auth_level == "admin":
        with tabs[2]: # Gerenciar
            if st.checkbox("Confirmar exclusão definitiva do ITEM"):
                if st.button("REMOVER ITEM AGORA", type="primary"):
                    conn = get_db_connection(); cur = conn.cursor()
                    cur.execute("DELETE FROM reservas WHERE item_codigo = %s", (item['codigo'],))
                    cur.execute("DELETE FROM itens WHERE codigo = %s", (item['codigo'],))
                    conn.commit(); conn.close(); st.rerun()

# --- PÁGINA: CATÁLOGO ---
def exibir_catalogo():
    st.title("📦 Catálogo")
    c1, c2 = st.columns([1, 2])
    busca = c1.text_input("🔍 Buscar...")
    
    if st.session_state.auth_level == "admin":
        ramos_filtro = c2.multiselect("⚜️ Ramos", LISTA_RAMOS, default=LISTA_RAMOS)
    else:
        # Usuário comum vê apenas seu ramo e o que é de "Grupo"
        ramos_filtro = [st.session_state.user_ramo, "Grupo"]

    conn = get_db_connection()
    if conn:
        df = pd.read_sql("SELECT * FROM itens ORDER BY codigo ASC", conn)
        conn.close()
        if not df.empty:
            df = df[df['ramo'].isin(ramos_filtro)]
            if busca:
                df = df[df.apply(lambda r: busca.lower() in str(r.values).lower(), axis=1)]

            cols = st.columns(4)
            for i, row in df.reset_index(drop=True).iterrows():
                with cols[i % 4]:
                    st.image(bytes(row['foto_blob']) if row['foto_blob'] else "https://via.placeholder.com/300", use_container_width=True)
                    st.markdown(f"**#{row['codigo']} {row['nome']}**")
                    st.caption(f"{row['ramo']}") # Exibe o ramo sob o nome
                    if st.button("Ver / Reservar", key=f"btn_cat_{row['codigo']}", use_container_width=True):
                        modal_detalhes(row)

# --- PÁGINA: AGENDA ---
def exibir_agenda():
    st.title("📅 Agenda Geral")
    conn = get_db_connection()
    if conn:
        if st.session_state.auth_level == "admin":
            query = "SELECT r.id, r.data_inicio, r.data_fim, r.usuario, i.nome, i.codigo, i.ramo FROM reservas r JOIN itens i ON r.item_codigo = i.codigo ORDER BY r.data_inicio ASC"
            df = pd.read_sql(query, conn)
        else:
            query = "SELECT r.id, r.data_inicio, r.data_fim, r.usuario, i.nome, i.codigo, i.ramo FROM reservas r JOIN itens i ON r.item_codigo = i.codigo WHERE i.ramo IN (%s, 'Grupo') ORDER BY r.data_inicio ASC"
            df = pd.read_sql(query, conn, params=(st.session_state.user_ramo,))
        conn.close()

        if not df.empty:
            hoje = date.today()
            st.write("Linhas em **verde** indicam equipamentos fora hoje.")
            for _, row in df.iterrows():
                cor = "#005555" if row['data_inicio'] <= hoje <= row['data_fim'] else "transparent"
                with st.container():
                    c1, c2, c3 = st.columns([3, 2, 1])
                    c1.markdown(f"<div style='background-color:{cor}; padding:5px; border-radius:5px;'><b>{row['nome']}</b> (#{row['codigo']})<br>{row['usuario']} ({row['ramo']})</div>", unsafe_allow_html=True)
                    c2.write(f"{row['data_inicio'].strftime('%d/%m')} - {row['data_fim'].strftime('%d/%m')}")
                    if st.session_state.auth_level == "admin":
                        if c3.button("Baixa", key=f"ag_del_{row['id']}"): deletar_reserva_sql(row['id'])
                st.divider()
        else: st.info("Nenhuma reserva ativa.")

# --- PÁGINA: CADASTRO ---
def exibir_cadastro():
    if st.session_state.auth_level != "admin": return
    st.title("➕ Cadastrar Item")
    with st.form("cad_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        cod = col1.text_input("Código")
        nome = col1.text_input("Nome")
        ramo = col2.selectbox("Ramo", LISTA_RAMOS) # "Grupo" aparece primeiro
        desc = st.text_area("Descrição")
        foto = st.file_uploader("Foto", type=['jpg', 'jpeg', 'png'])
        if st.form_submit_button("Salvar"):
            if cod and nome and foto:
                img = Image.open(foto)
                d = min(img.size); img = img.crop(((img.width-d)//2, (img.height-d)//2, (img.width+d)//2, (img.height+d)//2)).resize((300,300))
                buf = io.BytesIO(); img.convert("RGB").save(buf, format="JPEG", quality=50)
                conn = get_db_connection(); cur = conn.cursor()
                cur.execute("INSERT INTO itens (codigo, nome, descricao, ramo, foto_blob) VALUES (%s, %s, %s, %s, %s)", (cod, nome, desc, ramo, psycopg2.Binary(buf.getvalue())))
                conn.commit(); conn.close(); st.success("Salvo!")

# --- NAVEGAÇÃO ---
menu = ["📦 Catálogo", "📅 Agenda"]
if st.session_state.auth_level == "admin": menu.append("➕ Cadastrar")
opcao = st.sidebar.radio("Navegação", menu)
if st.sidebar.button("Sair"):
    st.session_state.auth_level = None; st.rerun()

if opcao == "📦 Catálogo": exibir_catalogo()
elif opcao == "📅 Agenda": exibir_agenda()
else: exibir_cadastro()