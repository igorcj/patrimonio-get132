import streamlit as st

def show_page(conn):
    st.title("⚜️ Catálogo de Equipamentos")
    
    busca = st.text_input("🔍 Filtrar por nome ou código")
    
    try:
        # Busca os itens
        df = conn.query("SELECT * FROM itens ORDER BY codigo ASC", ttl=0)
        
        if df.empty:
            st.warning("Nenhum item cadastrado ainda.")
            return

        # Filtro simples
        if busca:
            df = df[df['nome'].str.contains(busca, case=False) | df['codigo'].str.contains(busca)]

        # Grid
        cols = st.columns(4)
        for i, row in df.reset_index().iterrows():
            with cols[i % 4]:
                if row.get('foto_blob'):
                    st.image(row['foto_blob'], use_container_width=True)
                else:
                    st.image("https://via.placeholder.com/300?text=Sem+Foto", use_container_width=True)
                
                st.subheader(f"#{row['codigo']} {row['nome']}")
                st.write(f"Ramo: {row['ramo']}")
    except Exception as e:
        st.error(f"Erro ao carregar catálogo: {e}")