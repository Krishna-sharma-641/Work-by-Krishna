import streamlit as st
import pandas as pd
import json
from datetime import time
from scheduler import StudyScheduler      # original file names
from pdf_export import create_pdf

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

def _ensure_subject_defaults(subj: dict) -> dict:
    subj.setdefault("difficulty", 3)
    subj.setdefault("priority", 1)
    subj.setdefault("goal_hours", 0.0)
    return subj

def calculate_total_available_minutes(available_time: dict) -> int:
    from datetime import datetime
    total = 0
    for day, slots in available_time.items():
        for slot in slots:
            start, end = slot["start"], slot["end"]
            if start < end:
                delta = datetime.combine(datetime.today(), end) - datetime.combine(datetime.today(), start)
                total += int(delta.total_seconds() // 60)
    return total

def human_hours(minutes: int) -> str:
    h, m = minutes // 60, minutes % 60
    return f"{h}h {m}m" if h else f"{m}m"

def main():
    st.set_page_config(page_title="Smart Study Schedule Generator", page_icon="📚", layout="wide")

    st.markdown("<h1 style='text-align:center;'>📚 Smart Study Schedule Generator</h1>", unsafe_allow_html=True)

    if "subjects" not in st.session_state:
        st.session_state.subjects = []
    if "settings" not in st.session_state:
        st.session_state.settings = {
            "break_minutes": 10,
            "min_session_minutes": 30,
            "max_session_minutes": 120,
            "pomodoro_mode": False,
            "user_name": "",
        }

    # --- SIDEBAR ---
    with st.sidebar:
        st.header("⚙️ Preferences")

        # availability
        st.subheader("🕒 Available Study Time")
        available_time = {}
        for day in DAYS:
            st.markdown(f"**{day}**")   # 👈 now the day name shows

            if f"{day}_time_slots" not in st.session_state:
                st.session_state[f"{day}_time_slots"] = [{"start": time(9, 0), "end": time(12, 0)}]

            for i, slot in enumerate(st.session_state[f"{day}_time_slots"]):
                col1, col2, col3 = st.columns([3, 3, 1])
                with col1:
                    start = st.time_input("Start", slot["start"], key=f"{day}_start_{i}", label_visibility="collapsed")
                with col2:
                    end = st.time_input("End", slot["end"], key=f"{day}_end_{i}", label_visibility="collapsed")
                with col3:
                    if st.button("❌", key=f"{day}_remove_{i}"):
                        if len(st.session_state[f"{day}_time_slots"]) > 1:
                            st.session_state[f"{day}_time_slots"].pop(i)
                        st.rerun()
                st.session_state[f"{day}_time_slots"][i]["start"] = start
                st.session_state[f"{day}_time_slots"][i]["end"] = end

            if st.button("➕ Add slot", key=f"{day}_add"):
                st.session_state[f"{day}_time_slots"].append({"start": time(14, 0), "end": time(16, 0)})
                st.rerun()

            available_time[day] = st.session_state[f"{day}_time_slots"]
            st.markdown("---")

        # session rules
        st.subheader("🧠 Session Rules")
        st.session_state.settings["break_minutes"] = st.number_input("Break (min)", 0, 60, st.session_state.settings["break_minutes"])
        st.session_state.settings["min_session_minutes"] = st.slider("Min session", 15, 60, st.session_state.settings["min_session_minutes"])
        st.session_state.settings["max_session_minutes"] = st.slider("Max session", 60, 180, st.session_state.settings["max_session_minutes"], step=10)
        st.session_state.settings["pomodoro_mode"] = st.toggle("Pomodoro Mode (50m focus / 10m break)", st.session_state.settings["pomodoro_mode"])

        st.subheader("👤 Personalize")
        st.session_state.settings["user_name"] = st.text_input("Your name (for PDF)", st.session_state.settings["user_name"])

        # Save / Load
        st.subheader("💾 Save/Load")
        settings_export = {
            "subjects": st.session_state.subjects,
            "available_time": {
                d: [{"start": str(s["start"]), "end": str(s["end"])} for s in st.session_state[f"{d}_time_slots"]] for d in DAYS
            },
            "settings": st.session_state.settings,
        }
        st.download_button("⬇️ Download Settings", data=json.dumps(settings_export, indent=2), file_name="study_settings.json")

        uploaded = st.file_uploader("⬆️ Load Settings", type="json")
        if uploaded:
            try:
                data = json.load(uploaded)
                st.session_state.subjects = [_ensure_subject_defaults(s) for s in data.get("subjects", [])]
                for d in DAYS:
                    slots = []
                    for raw in data.get("available_time", {}).get(d, []):
                        h1, m1, *_ = map(int, raw["start"].split(":"))
                        h2, m2, *_ = map(int, raw["end"].split(":"))
                        slots.append({"start": time(h1, m1), "end": time(h2, m2)})
                    if slots:
                        st.session_state[f"{d}_time_slots"] = slots
                st.session_state.settings.update(data.get("settings", {}))
                st.success("Settings loaded")
                st.rerun()
            except Exception as e:
                st.error(f"Could not load: {e}")

    # --- MAIN ---
    st.header("📝 Subjects")
    new_subject = st.text_input("New subject")
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        new_diff = st.slider("Difficulty", 1, 5, 3, key="new_diff")
    with col2:
        new_prio = st.slider("Priority", 1, 3, 1, key="new_prio")
    with col3:
        new_goal = st.number_input("Goal hrs/wk", 0.0, 80.0, 0.0, step=0.5, key="new_goal")
    if st.button("Add Subject"):
        if new_subject and new_subject not in [s["name"] for s in st.session_state.subjects]:
            st.session_state.subjects.append({"name": new_subject, "difficulty": new_diff, "priority": new_prio, "goal_hours": new_goal})
            st.rerun()

    if st.session_state.subjects:
        to_remove = []
        for i, subj in enumerate(st.session_state.subjects):
            subj = _ensure_subject_defaults(subj)
            col1, col2, col3, col4, col5 = st.columns([3, 2, 2, 2, 1])
            with col1: st.write(f"**{subj['name']}**")
            with col2: subj["difficulty"] = st.slider("Diff", 1, 5, subj["difficulty"], key=f"diff_{i}")
            with col3: subj["priority"] = st.slider("Prio", 1, 3, subj["priority"], key=f"prio_{i}")
            with col4: subj["goal_hours"] = st.number_input("Goal", 0.0, 80.0, subj["goal_hours"], step=0.5, key=f"goal_{i}")
            with col5:
                if st.button("❌", key=f"sub_remove_{i}"):
                    to_remove.append(i)
            st.session_state.subjects[i] = subj
        for i in sorted(to_remove, reverse=True):
            st.session_state.subjects.pop(i)
        if to_remove: st.rerun()
    else:
        st.info("No subjects yet")

    st.header("📅 Generate Schedule")
    if st.button("✨ Generate Schedule", type="primary"):
        subject_list = [s["name"] for s in st.session_state.subjects]
        difficulties = {s["name"]: s["difficulty"] for s in st.session_state.subjects}
        priorities = {s["name"]: s["priority"] for s in st.session_state.subjects}
        goals_hours = {s["name"]: s["goal_hours"] for s in st.session_state.subjects}
        available_time = {d: st.session_state.get(f"{d}_time_slots", []) for d in DAYS}
        sset = st.session_state.settings

        scheduler = StudyScheduler(
            subject_list,
            difficulties,
            available_time,
            priorities=priorities,
            goals_hours=goals_hours,
            break_minutes=sset["break_minutes"],
            min_session_minutes=sset["min_session_minutes"],
            max_session_minutes=sset["max_session_minutes"],
            pomodoro_mode=sset["pomodoro_mode"],
        )
        with st.spinner("Generating..."):
            schedule = scheduler.generate_schedule()
            display_schedule(schedule)

            pdf_path = create_pdf(schedule, st.session_state.subjects, sset["user_name"])
            with open(pdf_path, "rb") as f:
                st.download_button("📄 Download PDF", data=f.read(), file_name="study_schedule.pdf", mime="application/pdf")

def display_schedule(schedule):
    st.subheader("📊 Schedule Overview")
    rows = []
    for day in DAYS:
        sessions = schedule.get(day, [])
        if sessions:
            for s in sessions:
                rows.append({"Day": day, "Time": f"{s['start'].strftime('%H:%M')} - {s['end'].strftime('%H:%M')}", "Subject": s['subject'], "Duration": f"{int(s['duration'])} min"})
        else:
            rows.append({"Day": day, "Time": "No sessions", "Subject": "-", "Duration": "-"})
    st.dataframe(pd.DataFrame(rows), use_container_width=True)

    st.subheader("📅 Weekly View")
    cols = st.columns(7)
    for i, day in enumerate(DAYS):
        with cols[i]:
            st.markdown(f"**{day}**")
            sessions = schedule.get(day, [])
            if sessions:
                for s in sessions:
                    st.markdown(f"<div style='background:#eef6ff; padding:4px; border-radius:4px; margin-bottom:4px;'><b>{s['start'].strftime('%H:%M')}–{s['end'].strftime('%H:%M')}</b><br>{s['subject']} ({int(s['duration'])}m)</div>", unsafe_allow_html=True)
            else:
                st.caption("No sessions")

if __name__ == "__main__":
    main()
