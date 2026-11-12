from datetime import date

import streamlit as st

import api_client
from api_client import ApiError

st.title("Mes échéances")
st.write("Ajoute les examens et rendus à préparer.")

try:
    courses = api_client.get_courses()
except ApiError as error:
    st.error(str(error))
    st.stop()

if not courses:
    st.info("Ajoute d'abord un cours dans la page Cours.")
else:
    course_by_name = {course["name"]: course["id"] for course in courses}
    with st.form("add_deadline_form"):
        course_name = st.selectbox("Cours", list(course_by_name))
        title = st.text_input("Nom de l'examen ou du rendu")
        deadline_date = st.date_input("Date", value=date.today())
        weight = st.slider("Importance", min_value=1, max_value=5, value=3)
        submitted = st.form_submit_button("Ajouter l'échéance")

    if submitted:
        if not title.strip():
            st.warning("Donne un nom à l'échéance.")
        else:
            try:
                api_client.add_deadline(
                    course_by_name[course_name],
                    title.strip(),
                    deadline_date,
                    weight,
                )
            except ApiError as error:
                st.error(str(error))
                st.stop()
            st.success("Échéance ajoutée.")

try:
    deadlines = api_client.get_deadlines()
except ApiError as error:
    st.error(str(error))
    st.stop()

course_names = {course["id"]: course["name"] for course in courses}
st.subheader("Échéances enregistrées")
if not deadlines:
    st.info("Aucune échéance enregistrée.")
else:
    for deadline in sorted(deadlines, key=lambda item: item["date"]):
        course_name = course_names.get(deadline["course_id"], "Cours inconnu")
        st.write(
            f"- **{deadline['title']}** — {course_name} — "
            f"{date.fromisoformat(deadline['date']).strftime('%d/%m/%Y')} "
            f"(importance : {deadline['weight']}/5)"
        )
