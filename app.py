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

# --- FUNÇÃO: LIMPEZA AUTOMÁTICA ---
def limpar_reservas_antigas():
    conn = get_db_connection()
    if conn:
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM reservas WHERE data_fim < CURRENT_DATE")
            conn.commit()
            cur.close()
            conn.close()
        except:
            pass

# --- PÁGINA: CATÁLOGO ---
def exibir_catalogo():
    st.title("📦 Catálogo de Equipamentos")
    
    # Filtros na Barra Lateral para o Catálogo
    st.sidebar.divider()
    st.sidebar.write("### Filtros")
    busca = st.sidebar.text_input("🔍 Busca rápida", placeholder="Nome ou código...")
    ramos_selecionados = st.sidebar.multiselect(
        "Filtrar por Ramo:", 
        ["Alcatéia", "Escoteiro", "Sênior", "Pioneiro", "Grupo"],
        default=["Alcatéia", "Escoteiro", "Sênior", "Pioneiro", "Grupo"]
    )
    
    conn = get_db_connection()
    if conn:
        df = pd.read_sql("SELECT * FROM itens ORDER BY codigo ASC", conn)
        conn.close()

        if not df.empty:
            # Aplicação dos Filtros
            if ramos_selecionados:
                df = df[df['ramo'].isin(ramos_selecionados)]
            if busca:
                df = df[df.apply(lambda r: busca.lower() in str(r.values).lower(), axis=1)]

            cols = st.columns(4)
            for i, row in df.reset_index(drop=True).iterrows():
                with cols[i % 4]:
                    # Imagem e Infos Básicas
                    st.image(bytes(row['foto_blob']) if row['foto_blob'] else "https://via.placeholder.com/300", use_container_width=True)
                    st.subheader(f"#{row['codigo']} {row['nome']}")
                    st.markdown(f"**Ramo:** {row['ramo']}")
                    st.caption(row['descricao'])
                    
                    # Seção de Detalhes e Ações
                    with st.expander("📅 Reservar / ⚙️ Gerenciar"):
                        # Aba de Reserva
                        st.write("**Nova Reserva:**")
                        with st.form(f"f_res_{row['codigo']}", clear_on_submit=True):
                            quem = st.text_input("Responsável")
                            d_ini = st.date_input("Início", min_value=datetime.now())
                            d_fim = st.date_input("Fim", min_value=d_ini)
                            if st.form_submit_button("Confirmar Reserva"):
                                if quem:
                                    reserva_sucesso = realizar_reserva_sql(row['codigo'], quem, d_ini, d_fim)
                                    if reserva_sucesso: st.success("Reserva feita!")
                        
                        st.divider()
                        # Aba de Exclusão (Com confirmação dupla)
                        st.write("⚠️ **Zona de Perigo**")
                        if st.checkbox(f"Desejo remover o item #{row['codigo']}", key=f"del_chk_{row['codigo']}"):
                            if st.button(f"CONFIRMAR EXCLUSÃO DEFINITIVA", key=f"del_btn_{row['codigo']}"):
                                remover_item_sql(row['codigo'])
                                st.rerun()

# --- FUNÇÕES SQL AUXILIARES ---
def realizar_reserva_sql(codigo, usuario, d_ini, d_fim):
    conn = get_db_connection()
    if conn:
        cur = conn.cursor()
        cur.execute("SELECT id FROM reservas WHERE item_codigo = %s AND NOT (data_fim < %s OR data_inicio > %s)", (codigo, d_ini, d_fim))
        if cur.fetchone():
            st.error("Item ocupado nesta data!")
            return False
        cur.execute("INSERT INTO reservas (item_codigo, usuario, data_inicio, data_fim) VALUES (%s, %s, %s, %s)", (codigo, usuario, d_ini, d_fim))
        conn.commit()
        conn.close()
        return True

def remover_item_sql(codigo):
    conn = get_db_connection()
    if conn:
        cur = conn.cursor()
        # Primeiro remove as reservas do item para não dar erro de chave estrangeira
        cur.execute("DELETE FROM reservas WHERE item_codigo = %s", (codigo,))
        cur.execute("DELETE FROM itens WHERE codigo = %s", (codigo,))
        conn.commit()
        conn.close()
        st.toast(f"Item {codigo} removido!")

# --- PÁGINA: AGENDA ---
def exibir_agenda():
    st.title("📅 Agenda de Ocupação")
    limpar_reservas_antigas() # Autolimpeza ao abrir
    
    conn = get_db_connection()
    if conn:
        query = """
            SELECT r.data_inicio, r.data_fim, r.usuario, i.nome, i.codigo 
            FROM reservas r 
            JOIN itens i ON r.item_codigo = i.codigo
            ORDER BY r.data_inicio ASC
        """
        df_res = pd.read_sql(query, conn)
        conn.close()

        if not df_res.empty:
            df_res['Período'] = df_res.apply(lambda x: f"{x['data_inicio'].strftime('%d/%m')} até {x['data_fim'].strftime('%d/%m')}", axis=1)
            st.table(df_res[['Período', 'codigo', 'nome', 'usuario']].rename(columns={'codigo': 'Cód.', 'nome': 'Item', 'usuario': 'Responsável'}))
        else:
            st.info("Nenhuma reserva ativa.")

# --- PÁGINA: CADASTRO ---
def exibir_cadastro():
    st.title("➕ Cadastrar Item")
    with st.form("cad_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        cod = col1.text_input("Código")
        nome = col1.text_input("Nome")
        ramo = col2.selectbox("Ramo", ["Alcatéia", "Escoteiro", "Sênior", "Pioneiro", "Grupo"])
        desc = st.text_area("Descrição")
        f_cam = st.camera_input("Tirar foto")
        f_up = st.file_uploader("Ou subir arquivo", type=['jpg', 'jpeg', 'png'])
        foto = f_cam if f_cam else f_up
        
        if st.form_submit_button("Salvar"):
            if cod and nome and foto:
                img = Image.open(foto)
                w, h = img.size
                d = min(w, h)
                img = img.crop(((w-d)//2, (h-d)//2, (w+d)//2, (h+d)//2)).resize((300,300))
                buf = io.BytesIO()
                img.convert("RGB").save(buf, format="JPEG", quality=50)
                
                conn = get_db_connection()
                if conn:
                    cur = conn.cursor()
                    cur.execute("INSERT INTO itens (codigo, nome, descricao, ramo, foto_blob) VALUES (%s, %s, %s, %s, %s)",
                                (cod, nome, desc, ramo, psycopg2.Binary(buf.getvalue())))
                    conn.commit()
                    conn.close()
                    st.success("Item salvo!")

# --- MENU LATERAL ---
st.sidebar.title("⚜️ GET 132")
opcao = st.sidebar.radio("Ir para:", ["📦 Catálogo", "📅 Agenda", "➕ Cadastrar"])

if opcao == "📦 Catálogo": exibir_catalogo()
elif opcao == "📅 Agenda": exibir_agenda()
else: exibir_cadastro()