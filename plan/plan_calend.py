# ==========================================
# 1. planner/priority.py
# ==========================================
from datetime import date, datetime, time, timedelta

try:
    from icalendar import Calendar, Event
except ImportError:  # pragma: no cover - depends on optional package
    Calendar = None
    Event = None


def calculate_priority(chapter: dict, deadline: dict, difficulty_weights: dict = None) -> float:
    """
    Calcule le score de priorité d'un chapitre en fonction de la proximité de l'échéance,
    du coefficient, de la difficulté et des heures restantes.
    """
    if difficulty_weights is None:
        difficulty_weights = {1: 1.0, 2: 1.5, 3: 2.0}

    remaining_hours = max(0.0, chapter.get("estimated_hours", 0.0) - chapter.get("completed_hours", 0.0))
    if remaining_hours == 0:
        return 0.0

    due_date = deadline.get("due_date")
    if isinstance(due_date, str):
        due_date = date.fromisoformat(due_date)
    elif isinstance(due_date, datetime):
        due_date = due_date.date()

    days_left = max(1, (due_date - date.today()).days)
    coefficient = float(deadline.get("coefficient", 1.0))
    difficulty = int(chapter.get("difficulty", 1))
    diff_weight = difficulty_weights.get(difficulty, 1.0)

    return (coefficient * diff_weight * remaining_hours) / days_left


# ==========================================
# 2. planner/constraints.py
# ==========================================
def validate_slot(start_dt: datetime, end_dt: datetime, due_date: date, existing_sessions: list) -> bool:
    """
    Vérifie qu'un créneau est valide :
    - Début strictement avant fin
    - Séance terminée avant la fin de la journée d'échéance
    - Aucun chevauchement avec les séances déjà planifiées
    """
    if start_dt >= end_dt:
        return False

    if isinstance(due_date, str):
        due_date = date.fromisoformat(due_date)
    elif isinstance(due_date, datetime):
        due_date = due_date.date()

    if start_dt.date() > due_date:
        return False

    for session in existing_sessions:
        if not (end_dt <= session["start_datetime"] or start_dt >= session["end_datetime"]):
            return False

    return True


def expand_weekly_availabilities(
    availabilities: list,
    start_date: date,
    max_end_date: date,
    max_session_minutes: int = 90
) -> list:
    """
    Transforme les disponibilités hebdomadaires récurrentes {weekday, start_time, end_time}
    en créneaux datés et découpés selon une durée optimale (par défaut 1h30 max).
    Note : weekday suit la convention Python (0 = Lundi ... 6 = Dimanche).
    """
    slots = []
    current_day = start_date

    while current_day <= max_end_date:
        day_avails = [a for a in availabilities if a["weekday"] == current_day.weekday()]
        for avail in day_avails:
            st = avail["start_time"]
            et = avail["end_time"]
            if isinstance(st, str):
                st = time.fromisoformat(st)
            if isinstance(et, str):
                et = time.fromisoformat(et)

            slot_start = datetime.combine(current_day, st)
            slot_end = datetime.combine(current_day, et)

            while slot_start < slot_end:
                chunk_end = min(slot_end, slot_start + timedelta(minutes=max_session_minutes))
                if (chunk_end - slot_start).total_seconds() >= 1800:  # Minimum 30 min par séance
                    slots.append((slot_start, chunk_end))
                slot_start = chunk_end

        current_day += timedelta(days=1)

    slots.sort(key=lambda x: x[0])
    return slots


# ==========================================
# 3. planner/scheduler.py
# ==========================================
def generate_schedule(
    chapters: list,
    deadlines: list,
    availabilities: list,
    start_date: date = None,
    existing_sessions: list = None
) -> dict:
    """
    Génère le planning hebdomadaire de révision.
    Retourne un dictionnaire contenant :
      - 'sessions': liste de {chapter_id, start_datetime, end_datetime}
      - 'unscheduled_hours': dictionnaire {chapter_id: heures_non_planifiées}
      - 'insufficient_time': booléen signalant si le temps disponible est insuffisant
    """
    if start_date is None:
        start_date = date.today()
    if existing_sessions is None:
        existing_sessions = []

    if not chapters or not availabilities or not deadlines:
        return {"sessions": [], "unscheduled_hours": {}, "insufficient_time": False}

    deadline_map = {d["course_id"]: d for d in deadlines}
    tasks = []
    max_due_date = start_date

    for ch in chapters:
        dl = deadline_map.get(ch["course_id"])
        if not dl:
            continue

        due = dl["due_date"]
        if isinstance(due, str):
            due = date.fromisoformat(due)
        elif isinstance(due, datetime):
            due = due.date()

        if due > max_due_date:
            max_due_date = due

        remaining = max(0.0, float(ch.get("estimated_hours", 0.0)) - float(ch.get("completed_hours", 0.0)))
        if remaining > 0:
            prio = calculate_priority(ch, dl)
            tasks.append({
                "chapter": ch,
                "due_date": due,
                "remaining_hours": remaining,
                "priority": prio
            })

    # Tri par priorité décroissante
    tasks.sort(key=lambda x: x["priority"], reverse=True)

    available_slots = expand_weekly_availabilities(availabilities, start_date, max_due_date)
    planned_sessions = list(existing_sessions)
    new_sessions = []

    for task in tasks:
        ch_id = task["chapter"]["id"]
        due_date = task["due_date"]

        for slot_start, slot_end in available_slots:
            if task["remaining_hours"] <= 0:
                break

            slot_duration_hours = (slot_end - slot_start).total_seconds() / 3600.0
            alloc_hours = min(task["remaining_hours"], slot_duration_hours)
            actual_end = slot_start + timedelta(hours=alloc_hours)

            if validate_slot(slot_start, actual_end, due_date, planned_sessions):
                session_obj = {
                    "chapter_id": ch_id,
                    "start_datetime": slot_start,
                    "end_datetime": actual_end
                }
                planned_sessions.append(session_obj)
                new_sessions.append(session_obj)
                task["remaining_hours"] = round(task["remaining_hours"] - alloc_hours, 2)

    unscheduled = {
        t["chapter"]["id"]: t["remaining_hours"]
        for t in tasks if t["remaining_hours"] > 0
    }

    return {
        "sessions": new_sessions,
        "unscheduled_hours": unscheduled,
        "insufficient_time": len(unscheduled) > 0
    }


def replan_skipped_sessions(
    all_sessions: list,
    chapters: list,
    deadlines: list,
    availabilities: list,
    reference_date: date = None
) -> dict:
    """
    Replanifie automatiquement les séances marquées 'skipped' dans les prochains
    créneaux libres avant l'échéance.
    Conserve les séances 'done' et 'planned' déjà validées.
    """
    if reference_date is None:
        reference_date = date.today()

    kept_sessions = [
        s for s in all_sessions
        if s.get("status") in ("done", "planned")
    ]

    # Les séances 'done' et 'planned' futures couvrent déjà une partie des heures
    planned_hours_by_chapter = {}
    for s in kept_sessions:
        dur = (s["end_datetime"] - s["start_datetime"]).total_seconds() / 3600.0
        planned_hours_by_chapter[s["chapter_id"]] = planned_hours_by_chapter.get(s["chapter_id"], 0.0) + dur

    adjusted_chapters = []
    for ch in chapters:
        ch_copy = dict(ch)
        already_covered = planned_hours_by_chapter.get(ch["id"], 0.0)
        ch_copy["completed_hours"] = max(float(ch.get("completed_hours", 0.0)), already_covered)
        adjusted_chapters.append(ch_copy)

    return generate_schedule(
        chapters=adjusted_chapters,
        deadlines=deadlines,
        availabilities=availabilities,
        start_date=reference_date,
        existing_sessions=kept_sessions
    )


# ==========================================
# 4. planner/calendar.py
# ==========================================
def generate_ics(sessions: list, chapters_map: dict) -> bytes:
    """
    Génère un fichier calendrier .ics valide avec un événement par séance.
    """
    if Calendar is None or Event is None:
        raise ImportError(
            "Le package 'icalendar' est requis pour générer un fichier .ics. "
            "Installez-le avec: py -m pip install icalendar"
        )

    cal = Calendar()
    cal.add("prodid", "-//StudyPlan//Planning Etudiant//FR")
    cal.add("version", "2.0")
    cal.add("calscale", "GREGORIAN")

    for idx, session in enumerate(sessions):
        event = Event()
        ch_id = session["chapter_id"]
        ch_info = chapters_map.get(ch_id, {})
        title = ch_info.get("title", f"Chapitre #{ch_id}")

        event.add("uid", f"studyplan-session-{ch_id}-{idx}@studyplan.local")
        event.add("summary", f"Révision : {title}")
        event.add("dtstart", session["start_datetime"])
        event.add("dtend", session["end_datetime"])
        event.add("dtstamp", datetime.now())
        event.add("description", f"Séance de révision StudyPlan - {title}")

        cal.add_component(event)

    return cal.to_ical()