import streamlit as st
import psycopg2
import pandas as pd
from PIL import Image
import io

st.set_page_config(page_title="Patrimônio GET 132", page_icon="⚜️", layout="wide")

# --- FUNÇÃO DE CONEXÃO (PSYCOPG2) ---
def get_db_connection():
    try:
        conn = psycopg2.connect(
            host=st.secrets["host"],
            port=st.secrets["port"],
            database=st.secrets["database"],
            user=st.secrets["user"],
            password=st.secrets["password"]
        )
        return conn
    except Exception as e:
        st.error(f"Erro ao conectar ao banco: {e}")
        return None

# --- PÁGINA: CATÁLOGO ---
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
                # Filtro dinâmico no DataFrame
                if busca:
                    df = df[df.apply(lambda r: busca.lower() in str(r.values).lower(), axis=1)]

                cols = st.columns(4)
                for i, row in df.reset_index(drop=True).iterrows():
                    with cols[i % 4]:
                        # Exibição da foto (blob para imagem)
                        if row['foto_blob'] is not None:
                            st.image(row['foto_blob'], use_container_width=True)
                        else:
                            st.image("https://via.placeholder.com/300x300?text=Sem+Foto", use_container_width=True)
                        
                        st.subheader(f"#{row['codigo']} {row['nome']}")
                        st.caption(f"Ramo: {row['ramo']}")
                        with st.expander("Ver detalhes"):
                            st.write(row['descricao'])
            else:
                st.info("Inventário vazio.")
        except Exception as e:
            st.error(f"Erro na consulta: {e}")

# --- PÁGINA: CADASTRO ---
def exibir_cadastro():
    st.title("➕ Cadastrar Novo Item")
    
    with st.form("form_cadastro", clear_on_submit=True):
        col1, col2 = st.columns(2)
        cod = col1.text_input("Código")
        nome = col1.text_input("Nome")
        ramo = col2.selectbox("Ramo", ["Alcatéia", "Escoteiro", "Sênior", "Pioneiro", "Grupo"])
        desc = st.text_area("Descrição")
        foto = st.file_uploader("Foto", type=['jpg', 'jpeg', 'png'])
        
        if st.form_submit_button("Salvar no Patrimônio"):
            if cod and nome and foto:
                # Processamento da imagem
                img = Image.open(foto)
                w, h = img.size
                d = min(w, h)
                img = img.crop(((w-d)//2, (h-d)//2, (w+d)//2, (h+d)//2)).resize((400,400))
                
                buffer = io.BytesIO()
                img.convert("RGB").save(buffer, format="JPEG", quality=60)
                foto_bytes = buffer.getvalue()
                
                # Inserção manual com psycopg2
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
                        st.success("Item cadastrado com sucesso!")
                    except Exception as e:
                        st.error(f"Erro ao salvar: {e}")
            else:
                st.warning("Preencha todos os campos e adicione uma foto.")

# --- MENU LATERAL ---
st.sidebar.title("⚜️ GET 132")
opcao = st.sidebar.radio("Navegação", ["Catálogo", "Cadastrar"])

if opcao == "Catálogo":
    exibir_catalogo()
else:
    exibir_cadastro()