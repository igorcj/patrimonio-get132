import streamlit as st
import psycopg2
import pandas as pd
from PIL import Image
import io

st.set_page_config(page_title="Patrimônio GET 132", page_icon="⚜️", layout="wide")

# Função para conectar ao banco usando psycopg2
def get_db_connection():
    try:
        conn = psycopg2.connect(
            host=st.secrets["host"],
            port=st.secrets["port"],
            database=st.secrets["database"],
            user=st.secrets["user"],
            password=st.secrets["password"],
            connect_timeout=10
        )
        return conn
    except Exception as e:
        st.error(f"Erro de Conexão: {e}")
        return None

# --- ABA: CATÁLOGO ---
def exibir_catalogo():
    st.title("⚜️ Catálogo de Equipamentos")
    busca = st.text_input("🔍 Buscar por nome, código ou descrição...")
    
    conn = get_db_connection()
    if conn:
        try:
            query = "SELECT id, codigo, nome, ramo, descricao, foto_blob FROM itens ORDER BY codigo ASC"
            df = pd.read_sql(query, conn)
            conn.close()

            if not df.empty:
                # Filtro dinâmico
                if busca:
                    mask = df.apply(lambda r: busca.lower() in str(r.values).lower(), axis=1)
                    df = df[mask]

                cols = st.columns(4)
                for i, row in df.reset_index(drop=True).iterrows():
                    with cols[i % 4]:
                        # Renderização da Imagem
                        if row['foto_blob'] is not None:
                            st.image(bytes(row['foto_blob']), use_container_width=True)
                        else:
                            st.image("https://via.placeholder.com/300x300?text=Sem+Foto", use_container_width=True)
                        
                        st.subheader(f"#{row['codigo']} {row['nome']}")
                        st.caption(f"Ramo: {row['ramo']}")
                        with st.expander("Ver Detalhes"):
                            st.write(row['descricao'])
            else:
                st.info("Nenhum item cadastrado.")
        except Exception as e:
            st.error(f"Erro ao carregar dados: {e}")

# --- ABA: CADASTRO ---
def exibir_cadastro():
    st.title("➕ Cadastrar Novo Item")
    with st.form("cad_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        cod = col1.text_input("Código (Ex: 001)")
        nome = col1.text_input("Nome do Item")
        ramo = col2.selectbox("Ramo", ["Alcatéia", "Escoteiro", "Sênior", "Pioneiro", "Grupo"])
        desc = st.text_area("Descrição")
        foto = st.file_uploader("Capturar ou subir Foto", type=['jpg', 'jpeg', 'png'])
        
        if st.form_submit_button("Salvar no Sistema"):
            if cod and nome and foto:
                # Processamento da Imagem: Quadrada e Leve
                img = Image.open(foto)
                w, h = img.size
                d = min(w, h)
                img = img.crop(((w-d)//2, (h-d)//2, (w+d)//2, (h+d)//2)).resize((400,400))
                
                buf = io.BytesIO()
                img.convert("RGB").save(buf, format="JPEG", quality=60)
                foto_bytes = buf.getvalue()
                
                conn = get_db_connection()
                if conn:
                    try:
                        cur = conn.cursor()
                        cur.execute(
                            "INSERT INTO itens (codigo, nome, descricao, ramo, foto_blob) VALUES (%s, %s, %s, %s, %s)",
                            (cod, nome, desc, ramo, psycopg2.Binary(foto_bytes))
                        )
                        conn.commit()
                        cur.close()
                        conn.close()
                        st.success(f"Item {nome} cadastrado!")
                    except Exception as e:
                        st.error(f"Erro ao salvar: {e}")
            else:
                st.warning("Preencha Código, Nome e Foto.")

# --- NAVEGAÇÃO ---
st.sidebar.title("GET 132")
opcao = st.sidebar.radio("Ir para:", ["📦 Catálogo", "➕ Cadastrar"])

if opcao == "📦 Catálogo":
    exibir_catalogo()
else:
    exibir_cadastro()