import streamlit as st

import api_client
from api_client import ApiError

st.title("Mes cours")
st.write("Importe un support PDF ou Markdown pour ajouter un cours.")

with st.form("import_course_form"):
    support = st.file_uploader("Support de cours", type=["pdf", "md", "markdown"])
    submitted = st.form_submit_button("Importer le cours")

if submitted:
    if support is None:
        st.warning("Choisis un fichier avant de l'importer.")
    else:
        try:
            course = api_client.upload_course(support.name, support.getvalue())
        except ApiError as error:
            st.error(str(error))
            st.stop()
        st.success(f"'{course.get('name', support.name)}' a été ajouté.")

try:
    courses = api_client.get_courses()
except ApiError as error:
    st.error(str(error))
    st.stop()

if not courses:
    st.info("Aucun cours pour le moment. Importe un support pour commencer.")
else:
    for course in courses:
        with st.container(border=True):
            st.subheader(course["name"])
            chapters = course.get("chapters", [])
            st.write(f"Chapitres : {', '.join(chapters) if chapters else 'À extraire'}")
            st.write(f"Charge estimée : {course.get('estimated_hours', 0)} h")
            progress = float(course.get("progress", 0))
            st.progress(min(max(progress / 100, 0.0), 1.0))
            st.caption(f"Avancement : {progress:.0f} %")
