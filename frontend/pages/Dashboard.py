from datetime import date, datetime

import streamlit as st

import api_client
from api_client import ApiError

st.title("Tableau de bord")
st.write("Un aperçu de tes cours, de tes séances et de tes prochaines échéances.")

try:
    courses = api_client.get_courses()
    deadlines = api_client.get_deadlines()
    sessions = api_client.get_plan(date.today().strftime("%G-W%V"))
except ApiError as error:
    st.error(str(error))
    st.stop()

done_sessions = [session for session in sessions if session["done"]]
late_sessions = [
    session
    for session in sessions
    if not session["done"] and datetime.fromisoformat(session["end"]) < datetime.now()
]
upcoming_deadlines = [
    deadline
    for deadline in deadlines
    if date.fromisoformat(deadline["date"]) >= date.today()
]

col1, col2, col3 = st.columns(3)
col1.metric("Cours", len(courses))
col2.metric("Séances faites cette semaine", len(done_sessions))
col3.metric("Séances en retard", len(late_sessions))

st.subheader("Avancement par cours")
if not courses:
    st.info("Importe un cours pour suivre ton avancement.")
else:
    for course in courses:
        progress = float(course.get("progress", 0))
        st.write(f"**{course['name']}** — {progress:.0f} %")
        st.progress(min(max(progress / 100, 0.0), 1.0))

st.subheader("Prochaines échéances")
if not upcoming_deadlines:
    st.info("Aucune échéance à venir.")
else:
    course_names = {course["id"]: course["name"] for course in courses}
    for deadline in sorted(upcoming_deadlines, key=lambda item: item["date"])[:5]:
        due_date = date.fromisoformat(deadline["date"])
        st.write(
            f"- **{deadline['title']}** — "
            f"{course_names.get(deadline['course_id'], 'Cours inconnu')} — "
            f"{due_date.strftime('%d/%m/%Y')}"
        )

st.subheader("Séances de la semaine")
if not sessions:
    st.info("Aucune séance planifiée cette semaine.")
else:
    for session in sessions:
        end = datetime.fromisoformat(session["end"])
        if session["done"]:
            status = "Terminée"
        elif end < datetime.now():
            status = "En retard"
        else:
            status = "À faire"
        st.write(
            f"- **{session['course_name']}** — {session['title']} — "
            f"{end.strftime('%d/%m à %H:%M')} — {status}"
        )
