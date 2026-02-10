import streamlit as st

st.set_page_config(page_title="Patrimônio GET 132", page_icon="⚜️")

st.title("⚜️ Grupo Escoteiro do Triângulo - 132")
st.subheader("Sistema de Gestão de Patrimônio")

st.write("Bem-vindo ao protótipo do nosso app!")

# Simulando uma entrada de dados simples
nome_item = st.text_input("Nome do equipamento (Ex: Barraca 2 pessoas)")
ramo = st.selectbox("Pertence ao Ramo:", ["Alcatéia", "Escoteiro", "Sênior", "Pioneiro", "Grupo"])

if st.button("Simular Cadastro"):
    st.success(f"Item '{nome_item}' registrado para o Ramo {ramo} com sucesso!")