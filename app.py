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

# --- LIMPEZA ---
def limpar_reservas_antigas():
    conn = get_db_connection()
    if conn:
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM reservas WHERE data_fim < CURRENT_DATE")
            conn.commit()
            cur.close()
            conn.close()
        except: pass

@st.dialog("Detalhes do Equipamento", width="large")
def modal_detalhes(item):
    st.write(f"### {item['nome']} (#{item['codigo']})")
    st.image(bytes(item['foto_blob']) if item['foto_blob'] else "https://via.placeholder.com/300")
    st.write(f"**Descrição:** {item['descricao']}")
    
    st.divider()
    tab1, tab2, tab3 = st.tabs(["📅 Reservar", "📋 Ocupação", "⚙️ Gerenciar"])
    
    with tab1:
        # Usamos chaves únicas para garantir que o Streamlit não perca as datas
        quem = st.text_input("Nome do Responsável", key=f"user_input_{item['codigo']}")
        d_ini = st.date_input("Data de Retirada", min_value=datetime.now().date(), key=f"start_{item['codigo']}")
        d_fim = st.date_input("Data de Devolução", min_value=d_ini, key=f"end_{item['codigo']}")
        
        if st.button("Confirmar Reserva", use_container_width=True):
            if not quem:
                st.warning("Por favor, informe quem é o responsável.")
            else:
                conn = get_db_connection()
                cur = conn.cursor()
                # Verifica conflito
                cur.execute("""
                    SELECT id FROM reservas 
                    WHERE item_codigo = %s AND NOT (data_fim < %s OR data_inicio > %s)
                """, (item['codigo'], d_ini, d_fim))
                
                if cur.fetchone():
                    st.error("⚠️ Este item já está reservado neste período!")
                else:
                    cur.execute(
                        "INSERT INTO reservas (item_codigo, usuario, data_inicio, data_fim) VALUES (%s, %s, %s, %s)",
                        (item['codigo'], quem, d_ini, d_fim)
                    )
                    conn.commit()
                    st.success("✅ Reserva realizada!")
                    st.rerun()
                conn.close()

    with tab2:
        conn = get_db_connection()
        df_res = pd.read_sql("SELECT usuario, data_inicio, data_fim FROM reservas WHERE item_codigo = %s ORDER BY data_inicio ASC", conn, params=(item['codigo'],))
        conn.close()
        if not df_res.empty:
            df_res.columns = ['Responsável', 'Início', 'Fim']
            st.table(df_res)
        else:
            st.info("Item livre em todas as datas.")

    with tab3:
        if st.checkbox("Confirmar exclusão definitiva do item"):
            if st.button("Remover agora", type="primary"):
                conn = get_db_connection()
                cur = conn.cursor()
                cur.execute("DELETE FROM reservas WHERE item_codigo = %s", (item['codigo'],))
                cur.execute("DELETE FROM itens WHERE codigo = %s", (item['codigo'],))
                conn.commit()
                conn.close()
                st.rerun()

# --- PÁGINA: CATÁLOGO ---
def exibir_catalogo():
    st.title("📦 Catálogo GET 132")
    
    # Filtros estáveis
    c1, c2 = st.columns([1, 2])
    busca = c1.text_input("🔍 Buscar...")
    ramos = c2.multiselect("⚜️ Ramos", ["Alcatéia", "Escoteiro", "Sênior", "Pioneiro", "Grupo"], default=["Alcatéia", "Escoteiro", "Sênior", "Pioneiro", "Grupo"])

    conn = get_db_connection()
    if conn:
        df = pd.read_sql("SELECT * FROM itens ORDER BY codigo ASC", conn)
        conn.close()

        if not df.empty:
            df = df[df['ramo'].isin(ramos)]
            if busca:
                df = df[df.apply(lambda r: busca.lower() in str(r.values).lower(), axis=1)]

            # Lógica para 1 coluna no celular (simulado por largura)
            cols = st.columns(4) # O Streamlit empilha em 1 col automaticamente no celular
            for i, row in df.reset_index(drop=True).iterrows():
                with cols[i % 4]:
                    st.image(bytes(row['foto_blob']) if row['foto_blob'] else "https://via.placeholder.com/300", use_container_width=True)
                    st.markdown(f"**#{row['codigo']} {row['nome']}**")
                    st.caption(f"Ramo: {row['ramo']}")
                    if st.button("Ver / Reservar", key=f"btn_cat_{row['codigo']}", use_container_width=True):
                        modal_detalhes(row)

# --- PÁGINA: AGENDA ---
def exibir_agenda():
    st.title("📅 Agenda de Reservas")
    limpar_reservas_antigas()
    
    conn = get_db_connection()
    if conn:
        df = pd.read_sql("""
            SELECT r.data_inicio, r.data_fim, r.usuario, i.nome, i.codigo 
            FROM reservas r JOIN itens i ON r.item_codigo = i.codigo
            ORDER BY r.data_inicio ASC
        """, conn)
        conn.close()

        if not df.empty:
            hoje = datetime.now().date()
            
            # Função de destaque corrigida: usamos os nomes exatos das colunas do DataFrame
            def destacar_hoje(row):
                # Importante: checar os nomes exatos retornados pelo SQL
                if row['data_inicio'] <= hoje <= row['data_fim']:
                    return ['background-color: #d1e7dd; color: #0f5132; font-weight: bold'] * len(row)
                return [''] * len(row)

            st.write("Linhas em **verde** indicam equipamentos fora do depósito hoje.")
            
            # Aplicamos o estilo ANTES de renomear as colunas para evitar o KeyError
            styled_df = df.style.apply(destacar_hoje, axis=1)
            
            # Renomeamos as colunas apenas na visualização
            df_view = df.rename(columns={'data_inicio': 'Início', 'data_fim': 'Fim', 'codigo': 'Cód', 'nome': 'Item', 'usuario': 'Responsável'})
            
            # Nota: O .style do pandas retorna um objeto que o st.dataframe entende
            st.dataframe(styled_df, use_container_width=True, hide_index=True)
        else:
            st.info("Nenhuma reserva ativa.")

# --- PÁGINA: CADASTRO ---
def exibir_cadastro():
    st.title("➕ Cadastrar Item")
    with st.form("cad_form", clear_on_submit=True):
        cod = st.text_input("Código")
        nome = st.text_input("Nome")
        ramo = st.selectbox("Ramo", ["Alcatéia", "Escoteiro", "Sênior", "Pioneiro", "Grupo"])
        desc = st.text_area("Descrição")
        foto = st.camera_input("Foto")
        if st.form_submit_button("Salvar"):
            if cod and nome and foto:
                img = Image.open(foto)
                d = min(img.size)
                img = img.crop(((img.width-d)//2, (img.height-d)//2, (img.width+d)//2, (img.height+d)//2)).resize((300,300))
                buf = io.BytesIO()
                img.convert("RGB").save(buf, format="JPEG", quality=50)
                conn = get_db_connection()
                cur = conn.cursor()
                cur.execute("INSERT INTO itens (codigo, nome, descricao, ramo, foto_blob) VALUES (%s, %s, %s, %s, %s)", (cod, nome, desc, ramo, psycopg2.Binary(buf.getvalue())))
                conn.commit()
                conn.close()
                st.success("Salvo!")

# --- NAVEGAÇÃO ---
opcao = st.sidebar.radio("Navegação", ["📦 Catálogo", "📅 Agenda", "➕ Cadastrar"])
if opcao == "📦 Catálogo": exibir_catalogo()
elif opcao == "📅 Agenda": exibir_agenda()
else: exibir_cadastro()