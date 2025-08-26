# scheduler.py
import math
from datetime import datetime, timedelta, time as dtime

class StudyScheduler:
    def __init__(self, subjects, difficulties, available_time, **kwargs):
        self.subjects = subjects
        self.difficulties = difficulties or {}
        self.available_time = available_time or {}
        self.priorities = kwargs.get("priorities", {s: 1 for s in self.subjects})
        self.goals_hours = kwargs.get("goals_hours", {s: 0.0 for s in self.subjects})
        self.break_minutes = int(kwargs.get("break_minutes", 10))
        self.min_session_minutes = int(kwargs.get("min_session_minutes", 30))
        self.max_session_minutes = int(kwargs.get("max_session_minutes", 120))
        self.pomodoro_mode = bool(kwargs.get("pomodoro_mode", False))
        self.schedule = {day: [] for day in self.available_time.keys()}

    def _slot_minutes(self, slot):
        start, end = slot["start"], slot["end"]
        if start >= end: return 0
        return int((datetime.combine(datetime.today(), end) - datetime.combine(datetime.today(), start)).total_seconds() // 60)

    def _time_add(self, t, mins):
        dt = datetime.combine(datetime.today(), t) + timedelta(minutes=mins)
        return dt.time()

    def generate_schedule(self):
        slot_map = {(d, i): self._slot_minutes(s) for d, slots in self.available_time.items() for i, s in enumerate(slots)}
        total_avail = sum(slot_map.values())
        if not self.subjects or total_avail <= 0: return self.schedule

        weights = {s: self.difficulties.get(s, 3) * self.priorities.get(s, 1) for s in self.subjects}
        total_weight = max(1, sum(weights.values()))
        goals = {s: int(self.goals_hours.get(s, 0.0) * 60) for s in self.subjects}
        target = {s: goals[s] for s in self.subjects}
        rem = total_avail - sum(target.values())
        if rem > 0:
            for s in self.subjects:
                target[s] += int(rem * (weights[s] / total_weight))
        remain = target.copy()

        def pick_subject():
            cands = [s for s in self.subjects if remain[s] >= self.min_session_minutes]
            return max(cands, key=lambda x: (remain[x]/max(1, weights[x])), default=None)

        for d, slots in self.available_time.items():
            for idx, slot in enumerate(slots):
                cur = slot["start"]
                end = slot["end"]
                while True:
                    left = (datetime.combine(datetime.today(), end) - datetime.combine(datetime.today(), cur)).total_seconds() // 60
                    if left < self.min_session_minutes: break
                    subj = pick_subject()
                    if not subj: break
                    dur = min(remain[subj], self.max_session_minutes, left)
                    if dur < self.min_session_minutes: break
                    s_end = self._time_add(cur, dur)
                    self.schedule[d].append({"subject": subj, "start": cur, "end": s_end, "duration": int(dur), "slot_idx": idx})
                    remain[subj] -= int(dur)
                    cur = self._time_add(s_end, self.break_minutes)
        for d in self.schedule: self.schedule[d].sort(key=lambda x: x["start"])
        return self.schedule
