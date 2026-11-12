from datetime import date, datetime, time, timedelta

import streamlit as st

import api_client
from api_client import ApiError

st.title("Mon planning")
st.write("Indique tes créneaux libres, puis génère ton planning de révision.")

weekdays = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
try:
    current_slots = api_client.get_availability()
except ApiError as error:
    st.error(str(error))
    st.stop()
current_slots = st.session_state.get(
    "studyplan_availability_draft",
    current_slots,
)

with st.form("availability_form"):
    day_name = st.selectbox("Jour disponible", weekdays)
    col1, col2 = st.columns(2)
    start_time = col1.time_input("Début", value=time(9, 0))
    end_time = col2.time_input("Fin", value=time(12, 0))
    save_slot = st.form_submit_button("Ajouter ce créneau")

if save_slot:
    if end_time <= start_time:
        st.warning("L'heure de fin doit être après l'heure de début.")
    else:
        day_number = weekdays.index(day_name)
        slots = current_slots + [
            {
                "weekday": day_number,
                "start": start_time.strftime("%H:%M"),
                "end": end_time.strftime("%H:%M"),
            }
        ]
        try:
            api_client.save_availability(slots)
        except ApiError as error:
            st.error(str(error))
            st.stop()
        st.session_state["studyplan_availability_draft"] = slots
        st.success("Créneau ajouté à tes disponibilités.")
        st.rerun()

st.subheader("Mes créneaux disponibles")
if not current_slots:
    st.info("Aucun créneau disponible n'est enregistré.")
else:
    for slot in current_slots:
        st.write(
            f"- {weekdays[slot['weekday']]} : {slot['start']}–{slot['end']}"
        )

if st.button("Générer le planning de la semaine", type="primary"):
    try:
        api_client.generate_plan()
    except ApiError as error:
        st.error(str(error))
        st.stop()
    st.success("Planning généré.")

monday = date.today() - timedelta(days=date.today().weekday())
week_options = [
    (monday + timedelta(weeks=offset)).strftime("%G-W%V")
    for offset in range(4)
]
week = st.selectbox("Semaine à afficher", week_options)

try:
    sessions = api_client.get_plan(week)
except ApiError as error:
    st.error(str(error))
    st.stop()

st.subheader(f"Séances de la semaine {week}")
if not sessions:
    st.info("Aucune séance pour cette semaine. Génère ton planning pour commencer.")
else:
    for session in sessions:
        start = datetime.fromisoformat(session["start"])
        end = datetime.fromisoformat(session["end"])
        label = (
            f"{weekdays[start.weekday()]} {start.strftime('%d/%m à %H:%M')} — "
            f"{session['course_name']} : "
            f"{session['title']} ({end.strftime('%H:%M')})"
        )
        with st.container(border=True):
            st.write(label)
            checkbox_key = f"done_{session['id']}"
            if checkbox_key not in st.session_state:
                st.session_state[checkbox_key] = session["done"]
            done = st.checkbox("Séance terminée", key=checkbox_key)
            if done != session["done"]:
                try:
                    api_client.update_session(session["id"], done)
                except ApiError as error:
                    st.error(str(error))
                    st.stop()
                st.rerun()

try:
    calendar = api_client.get_calendar()
except ApiError as error:
    st.error(str(error))
    st.stop()

if sessions:
    st.download_button(
        "Télécharger le planning (.ics)",
        data=calendar,
        file_name="studyplan.ics",
        mime="text/calendar",
    )
