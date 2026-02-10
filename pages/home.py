import streamlit as st

st.title("⚜️ Catálogo de Equipamentos")

# Conexão com Supabase (PostgreSQL)
conn = st.connection("postgresql", type="sql")

# --- BUSCA E FILTRO ---
busca = st.text_input("🔍 Procure por nome, código ou descrição...", "").lower()

query = "SELECT * FROM itens"
df = conn.query(query, ttl=0) # ttl=0 para sempre pegar dados novos

if not df.empty:
    # Filtro em memória para facilitar busca dinâmica
    df_filtrado = df[
        df['nome'].str.lower().contains(busca) | 
        df['codigo'].str.contains(busca) |
        df['descricao'].str.lower().contains(busca)
    ]

    cols = st.columns(4)
    for i, row in df_filtrado.reset_index().iterrows():
        with cols[i % 4]:
            if row['foto_blob']:
                st.image(row['foto_blob'], use_container_width=True)
            else:
                st.image("https://via.placeholder.com/300?text=Sem+Foto", use_container_width=True)
            
            st.markdown(f"**#{row['codigo']} - {row['nome']}**")
            st.caption(f"Ramo: {row['ramo']}")
            
            with st.expander("Reservar"):
                st.write(row['descricao'])
                with st.form(key=f"res_{row['codigo']}"):
                    quem = st.text_input("Nome do Responsável")
                    data = st.date_input("Data da Retirada")
                    if st.form_submit_button("Confirmar Reserva"):
                        with conn.session as s:
                            s.execute(
                                "INSERT INTO reservas (item_codigo, usuario, data_inicio, data_fim) VALUES (:c, :u, :d, :d)",
                                {"c": row['codigo'], "u": quem, "d": data}
                            )
                            s.commit()
                        st.success("Reservado!")
else:
    st.info("Nenhum item cadastrado no sistema.")