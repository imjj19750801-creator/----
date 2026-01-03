# model.py
from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class Student:
    name: str = ""
    scores: Dict[str, float] = field(default_factory=dict)
    phone: str = ""
    note: str = ""

    def set_score(self, subject: str, value: float):
        self.scores[subject] = float(value)

    def get_score(self, subject: str) -> float:
        return float(self.scores.get(subject, 0.0))


@dataclass
class GradeBook:
    subjects: List[str] = field(default_factory=list)
    students: List[Student] = field(default_factory=list)

    def add_subject(self, subj: str):
        if subj and subj not in self.subjects:
            self.subjects.append(subj)
            for s in self.students:
                s.scores.setdefault(subj, 0.0)

    def remove_subject(self, subj: str):
        if subj in self.subjects:
            self.subjects.remove(subj)
            for s in self.students:
                s.scores.pop(subj, None)

    def add_student(self, name: str = "") -> Student:
        st = Student(name=name)
        for subj in self.subjects:
            st.scores.setdefault(subj, 0.0)
        self.students.append(st)
        return st

    def remove_student(self, index: int):
        if 0 <= index < len(self.students):
            self.students.pop(index)
