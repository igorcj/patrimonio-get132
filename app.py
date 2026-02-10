import streamlit as st
import psycopg2
import pandas as pd
from PIL import Image
import io
from datetime import datetime, timedelta

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

# --- FUNÇÃO AUXILIAR: RESERVAS ---
def salvar_reserva(codigo, usuario, d_inicio, d_fim):
    conn = get_db_connection()
    if conn:
        try:
            cur = conn.cursor()
            # Verifica se já existe reserva no período
            cur.execute("""
                SELECT id FROM reservas 
                WHERE item_codigo = %s AND NOT (data_fim < %s OR data_inicio > %s)
            """, (codigo, d_inicio, d_fim))
            
            if cur.fetchone():
                st.error("⚠️ Este item já está reservado em parte desse período!")
                return False
            
            cur.execute(
                "INSERT INTO reservas (item_codigo, usuario, data_inicio, data_fim) VALUES (%s, %s, %s, %s)",
                (codigo, usuario, d_inicio, d_fim)
            )
            conn.commit()
            cur.close()
            conn.close()
            return True
        except Exception as e:
            st.error(f"Erro ao reservar: {e}")
    return False

# --- PÁGINA: CATÁLOGO ---
def exibir_catalogo():
    st.title("📦 Catálogo e Reservas")
    busca = st.text_input("🔍 Buscar item...")
    
    conn = get_db_connection()
    if conn:
        df = pd.read_sql("SELECT * FROM itens ORDER BY codigo ASC", conn)
        conn.close()

        if not df.empty:
            if busca:
                df = df[df.apply(lambda r: busca.lower() in str(r.values).lower(), axis=1)]

            cols = st.columns(4)
            for i, row in df.reset_index(drop=True).iterrows():
                with cols[i % 4]:
                    st.image(bytes(row['foto_blob']) if row['foto_blob'] else "https://via.placeholder.com/300", use_container_width=True)
                    st.subheader(f"#{row['codigo']} {row['nome']}")
                    
                    with st.expander("📝 Reservar este item"):
                        with st.form(f"f_res_{row['codigo']}"):
                            quem = st.text_input("Nome do Responsável")
                            d_ini = st.date_input("Início da Reserva", min_value=datetime.now())
                            d_fim = st.date_input("Fim da Reserva", min_value=d_ini)
                            
                            if st.form_submit_button("Confirmar Reserva"):
                                if quem and salvar_reserva(row['codigo'], quem, d_ini, d_fim):
                                    st.success(f"Reservado para {quem}!")
                                    st.balloons()

# --- PÁGINA: AGENDA/CALENDÁRIO ---
def exibir_agenda():
    st.title("📅 Agenda de Ocupação")
    
    conn = get_db_connection()
    if conn:
        # Join para pegar o nome do item também
        query = """
            SELECT r.data_inicio, r.data_fim, r.usuario, i.nome, i.codigo 
            FROM reservas r 
            JOIN itens i ON r.item_codigo = i.codigo
            WHERE r.data_fim >= CURRENT_DATE
            ORDER BY r.data_inicio ASC
        """
        df_res = pd.read_sql(query, conn)
        conn.close()

        if not df_res.empty:
            # Visão de Tabela Organizada por Dia
            st.write("Abaixo estão os itens que estão fora ou sairão em breve:")
            
            # Formatação para exibição
            df_res['Período'] = df_res.apply(lambda x: f"{x['data_inicio'].strftime('%d/%m')} até {x['data_fim'].strftime('%d/%m')}", axis=1)
            df_res_display = df_res[['Período', 'codigo', 'nome', 'usuario']].rename(columns={
                'codigo': 'Cód.', 'nome': 'Equipamento', 'usuario': 'Quem Reservou'
            })
            
            st.table(df_res_display)
            
            # Dica de Visão de "Hoje"
            hoje = datetime.now().date()
            em_uso = df_res[(df_res['data_inicio'] <= hoje) & (df_res['data_fim'] >= hoje)]
            if not em_uso.empty:
                st.warning(f"🚨 Atualmente {len(em_uso)} itens estão em uso hoje!")
        else:
            st.info("Não há reservas futuras registradas.")

# --- PÁGINA: CADASTRO (Mantenha a que já temos) ---
def exibir_cadastro():
    st.title("➕ Cadastrar Item")
    # ... (mesmo código da câmera que enviamos anteriormente) ...
    with st.form("cad_form", clear_on_submit=True):
        cod = st.text_input("Código")
        nome = st.text_input("Nome")
        ramo = st.selectbox("Ramo", ["Alcatéia", "Escoteiro", "Sênior", "Pioneiro", "Grupo"])
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
                    st.success("Salvo!")

# --- NAVEGAÇÃO ---
st.sidebar.title("⚜️ GET 132")
opcao = st.sidebar.radio("Ir para:", ["📦 Catálogo", "📅 Agenda", "➕ Cadastrar"])

if opcao == "📦 Catálogo": exibir_catalogo()
elif opcao == "📅 Agenda": exibir_agenda()
else: exibir_cadastro()