import streamlit as st

st.set_page_config(page_title="Patrimônio GET 132", page_icon="⚜️", layout="wide")

# Função de conexão com tratamento de erro IPv4/Pooler
def get_conn():
    try:
        return st.connection("postgresql", type="sql")
    except Exception as e:
        st.error("Erro na conexão com o Banco. Verifique se o Host do Pooler está correto.")
        return None

conn = get_conn()

# --- LOGIN ---
if "auth" not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    st.title("⚜️ Acesso GET 132")
    if st.text_input("Senha", type="password") == "132132":
        st.session_state.auth = True
        st.rerun()
    st.stop()

# --- NAVEGAÇÃO ---
menu = st.sidebar.radio("Menu", ["Catálogo", "Cadastrar"])

if menu == "Catálogo":
    import pages.home as home
    home.show_page(conn)
else:
    import pages.cadastro as cadastro
    cadastro.show_page(conn)