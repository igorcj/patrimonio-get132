import streamlit as st
import psycopg2
import pandas as pd
from PIL import Image
import io
from datetime import datetime, date

st.set_page_config(page_title="Patrimônio GET 132", page_icon="⚜️", layout="wide")

LISTA_RAMOS = ["Grupo", "Alcatéia", "Escoteiro", "Sênior", "Pioneiro"]
LISTA_ESTADOS = ["Novo", "Bom", "Desgastado", "Manutenção"]

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

# --- LÓGICA DE LOGIN (Mantida conforme sua versão) ---
if "auth_level" not in st.session_state:
    st.session_state.auth_level = None
if st.session_state.auth_level is None:
    st.title("⚜️ Acesso ao Patrimônio - GET 132")
    user_type = st.selectbox("Selecione seu usuário:", ["Selecionar...", "Admin"] + LISTA_RAMOS[1:])
    senha = st.text_input("Senha:", type="password")
    if st.button("Entrar"):
        # ... (sua lógica de validação de senhas do secrets)
        # Simplificado para o exemplo, use sua lógica de if/elifs aqui
        if user_type == "Admin" and senha == st.secrets["senha_admin"]:
            st.session_state.auth_level = "admin"; st.session_state.user_ramo = "Todos"; st.rerun()
        # Adicionar os outros elifs de ramos aqui...
    st.stop()

# --- MODAL DETALHES (Com lógica de Consumível) ---
@st.dialog("Detalhes do Equipamento", width="large")
def modal_detalhes(item):
    st.write(f"### {item['nome']} (#{item['codigo']})")
    st.image(bytes(item['foto_blob']) if item['foto_blob'] else "https://via.placeholder.com/300")
    
    col_inf1, col_inf2, col_inf3 = st.columns(3)
    col_inf1.metric("Qtd Atual", item['quantidade_atual'])
    col_inf2.metric("Estado", item['estado'])
    col_inf3.metric("Tipo", "Consumível" if item['consumivel'] else "Permanente")

    st.markdown(f"**Descrição:** {item['descricao']}")
    st.divider()
    
    tab_res, tab_ocu = st.tabs(["📝 Retirada/Reserva", "📋 Histórico"])
    
    with tab_res:
        if item['consumivel']:
            st.info("Itens consumíveis são debitados do estoque imediatamente.")
            qtd_retirar = st.number_input("Quantidade a retirar", min_value=1, max_value=item['quantidade_atual'], step=1)
            if st.button("Confirmar Retirada (Baixa no Estoque)"):
                conn = get_db_connection()
                cur = conn.cursor()
                cur.execute("UPDATE itens SET quantidade_atual = quantidade_atual - %s WHERE codigo = %s", (qtd_retirar, item['codigo']))
                conn.commit(); conn.close()
                st.success("Estoque atualizado!"); st.rerun()
        else:
            # Lógica de reserva para não-consumíveis (permanece a sua)
            quem = st.text_input("Responsável")
            d_ini = st.date_input("Retirada", value=date.today(), min_value=date.today())
            d_fim = st.date_input("Devolução", value=d_ini, min_value=d_ini)
            if st.button("Agendar Reserva"):
                # ... (sua lógica de insert em reservas)
                st.success("Reservado!"); st.rerun()

# --- PÁGINA: MANUTENÇÃO DE ESTOQUE (ADMIN) ---
def exibir_manutencao():
    st.title("🔧 Gestão de Estoque e Manutenção")
    conn = get_db_connection()
    if conn:
        df = pd.read_sql("SELECT codigo, nome, ramo, quantidade_atual, quantidade_minima, estado FROM itens", conn)
        conn.close()
        
        # Filtro de Alerta
        abaixo_min = df[df['quantidade_atual'] < df['quantidade_minima']]
        no_limite = df[df['quantidade_atual'] == df['quantidade_minima']]
        
        st.subheader("🚨 Alerta de Reposição")
        for _, row in abaixo_min.iterrows():
            st.error(f"**{row['nome']}** (#{row['codigo']}) - Estoque: {row['quantidade_atual']} (Mínimo: {row['quantidade_minima']})")
        
        for _, row in no_limite.iterrows():
            st.warning(f"**{row['nome']}** (#{row['codigo']}) - Estoque no limiar: {row['quantidade_atual']}")

        st.divider()
        st.subheader("📊 Tabela Geral de Desgaste")
        st.dataframe(df.style.apply(lambda x: ['color: red' if x.estado == 'Manutenção' else '' for i in x], axis=1), use_container_width=True)

# --- PÁGINA: CADASTRO (Atualizada com novos campos) ---
def exibir_cadastro():
    st.title("➕ Cadastrar Novo Item")
    with st.form("cad_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        cod = c1.text_input("Código")
        nome = c1.text_input("Nome")
        ramo = c2.selectbox("Ramo", LISTA_RAMOS)
        estado = c2.selectbox("Estado de Conservação", LISTA_ESTADOS)
        
        c3, c4, c5 = st.columns(3)
        consumivel = c3.checkbox("É Consumível?")
        qtd_ini = c4.number_input("Quantidade Inicial", min_value=1, value=1)
        qtd_min = c5.number_input("Quantidade Mínima", min_value=0, value=1)
        
        desc = st.text_area("Descrição")
        foto = st.file_uploader("Foto", type=['jpg', 'png'])
        
        if st.form_submit_button("Salvar Item"):
            # ... (Lógica de processamento de imagem e INSERT no banco com os novos campos)
            pass

# --- NAVEGAÇÃO ---
menu = ["📦 Catálogo", "📅 Agenda"]
if st.session_state.auth_level == "admin":
    menu.extend(["➕ Cadastrar", "🔧 Manutenção"])

opcao = st.sidebar.radio("Navegação", menu)
# ... (lógica de roteamento das funções)