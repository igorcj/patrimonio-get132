import streamlit as st
from PIL import Image
import io

st.title("➕ Cadastro de Patrimônio")
conn = st.connection("postgresql", type="sql")

with st.form("cadastro_form", clear_on_submit=True):
    col1, col2 = st.columns(2)
    with col1:
        codigo = st.text_input("Código do Item (ex: 132-001)")
        nome = st.text_input("Nome do Equipamento")
    with col2:
        ramo = st.selectbox("Ramo Responsável", ["Alcatéia", "Escoteiro", "Sênior", "Pioneiro", "Grupo"])
        descricao = st.text_input("Breve Descrição")

    # Upload da Imagem
    foto_upload = st.file_uploader("Tire uma foto ou suba um arquivo", type=['jpg', 'jpeg', 'png'])

    if st.form_submit_button("Cadastrar Item"):
        if not (codigo and nome and foto_upload):
            st.error("Por favor, preencha código, nome e adicione uma foto.")
        else:
            # --- PROCESSAMENTO DA IMAGEM ---
            img = Image.open(foto_upload)
            
            # Cortar para Quadrado (Center Crop)
            w, h = img.size
            min_dim = min(w, h)
            img = img.crop(((w - min_dim) / 2, (h - min_dim) / 2, (w + min_dim) / 2, (h + min_dim) / 2))
            
            # Redimensionar e Comprimir
            img = img.resize((400, 400)) # 400x400 é um bom balanço
            img_byte_arr = io.BytesIO()
            img.convert("RGB").save(img_byte_arr, format='JPEG', quality=60)
            foto_bytes = img_byte_arr.getvalue()

            try:
                with conn.session as s:
                    s.execute(
                        "INSERT INTO itens (codigo, nome, descricao, ramo, foto_blob) VALUES (:c, :n, :d, :r, :f)",
                        {"c": codigo, "n": nome, "d": descricao, "r": ramo, "f": foto_bytes}
                    )
                    s.commit()
                st.success(f"Item {nome} salvo com sucesso!")
            except Exception as e:
                st.error(f"Erro ao salvar no banco: {e}")

if st.button("⬅️ Voltar para o Catálogo"):
    st.switch_page("pages/home.py")