import streamlit as st

st.set_page_config(page_title="Patrimônio GET 132", page_icon="⚜️", layout="wide")

st.sidebar.title("⚜️ Menu GET 132")
page = st.sidebar.radio("Navegação", ["Início / Catálogo", "Cadastrar Novo Item"])

if page == "Início / Catálogo":
    st.switch_page("pages/home.py")
elif page == "Cadastrar Novo Item":
    st.switch_page("pages/cadastro.py")