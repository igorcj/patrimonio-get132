import streamlit as st
import pandas as pd
from PIL import Image
import io

st.set_page_config(page_title="Patrimônio GET 132", page_icon="⚜️", layout="wide")

# Conexão robusta usando a URL dos Secrets
conn = st.connection("postgresql", type="sql")

# --- FUNÇÕES DE INTERFACE ---
def exibir_catalogo():
    st.title("⚜️ Catálogo de Equipamentos")
    
    # Busca
    busca = st.text_input("🔍 Buscar por nome, código ou descrição...", placeholder="Ex: Barraca, 001, Sênior...")
    
    try:
        df = conn.query("SELECT * FROM itens ORDER BY codigo ASC", ttl=0)
        
        if df.empty:
            st.info("O inventário está vazio. Vá em 'Cadastrar' para adicionar itens.")
            return

        # Filtro dinâmico
        if busca:
            mask = df.apply(lambda r: busca.lower() in str(r.values).lower(), axis=1)
            df = df[mask]

        # Grid de Exibição
        cols = st.columns(4)
        for i, row in df.reset_index(drop=True).iterrows():
            with cols[i % 4]:
                if row.get('foto_blob'):
                    st.image(row['foto_blob'], use_container_width=True)
                else:
                    st.image("https://via.placeholder.com/300x300?text=Sem+Foto", use_container_width=True)
                
                st.subheader(f"#{row['codigo']} {row['nome']}")
                st.caption(f"**Ramo:** {row['ramo']}")
                
                with st.expander("Detalhes / Reservar"):
                    st.write(f"**Descrição:** {row['descricao']}")
                    st.divider()
                    st.write("📅 **Simular Reserva**")
                    nome_res = st.text_input("Seu nome", key=f"user_{row['id']}")
                    if st.button("Confirmar", key=f"btn_{row['id']}"):
                        st.success(f"Reserva para {nome_res} anotada!")

    except Exception as e:
        st.error(f"Erro ao acessar o banco: {e}")

def exibir_cadastro():
    st.title("➕ Novo Item no Patrimônio")
    
    with st.form("form_cadastro", clear_on_submit=True):
        col1, col2 = st.columns(2)
        cod = col1.text_input("Código do Item (ex: 001)")
        nome = col1.text_input("Nome do Equipamento")
        ramo = col2.selectbox("Ramo", ["Alcatéia", "Escoteiro", "Sênior", "Pioneiro", "Grupo"])
        desc = st.text_area("Descrição / Estado de conservação")
        
        uploaded_file = st.file_uploader("Foto do Item", type=['jpg', 'jpeg', 'png'])
        
        if st.form_submit_button("Salvar Item"):
            if cod and nome and uploaded_file:
                # Processamento da imagem: Quadrada, 400x400, JPEG 60%
                img = Image.open(uploaded_file)
                w, h = img.size
                min_dim = min(w, h)
                img = img.crop(((w - min_dim) // 2, (h - min_dim) // 2, (w + min_dim) // 2, (h + min_dim) // 2))
                img = img.resize((400, 400))
                
                buffer = io.BytesIO()
                img.convert("RGB").save(buffer, format="JPEG", quality=60)
                foto_bytes = buffer.getvalue()
                
                try:
                    with conn.session as s:
                        s.execute(
                            "INSERT INTO itens (codigo, nome, descricao, ramo, foto_blob) VALUES (:c, :n, :d, :r, :f)",
                            {"c": cod, "n": nome, "d": desc, "r": ramo, "f": foto_bytes}
                        )
                        s.commit()
                    st.success(f"Item {nome} cadastrado com sucesso!")
                except Exception as e:
                    st.error(f"Erro ao salvar: {e}")
            else:
                st.warning("Preencha Código, Nome e adicione uma Foto.")

# --- NAVEGAÇÃO LATERAL ---
st.sidebar.image("https://escolatransformar.com.br/wp-content/uploads/2021/04/escoteiro-logo.png", width=100) # Opcional: logo do grupo
st.sidebar.title("GET 132")
opcao = st.sidebar.radio("Navegação", ["📦 Catálogo", "➕ Cadastrar Item"])

if opcao == "📦 Catálogo":
    exibir_catalogo()
else:
    exibir_cadastro()