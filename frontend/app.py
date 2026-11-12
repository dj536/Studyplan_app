import streamlit as st

import api_client

st.set_page_config(page_title="StudyPlan", page_icon="📚")

st.title("StudyPlan")
st.write("Organise tes révisions, tes échéances et ton planning.")

if api_client.using_mock_data():
    st.info("Mode démo : les données affichées sont fictives.")
else:
    st.success("Connecté au serveur StudyPlan.")

st.subheader("Pour commencer")
st.write(
    "Ajoute tes cours et leurs échéances, indique tes disponibilités, "
    "puis génère ton planning de révision."
)
st.write("Utilise le menu à gauche pour ouvrir le tableau de bord ou les autres pages.")
