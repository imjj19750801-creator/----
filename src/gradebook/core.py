# src/gradebook/core.py
from typing import Any, Dict, List

from .model import GradeBook


def grade_from_avg(avg: float) -> str:
    if avg >= 90:
        return "A"
    if avg >= 80:
        return "B"
    if avg >= 70:
        return "C"
    if avg >= 60:
        return "D"
    return "F"


def recalculate(gradebook: GradeBook) -> List[Dict[str, Any]]:
    """
    GradeBook을 받아 학생별 총점/평균/등급/석차를 계산한 리스트 반환.

    반환 항목: {
        'student': Student,
        'total': float,
        'avg': float,
        'grade': str,
        'rank': int | None
    }
    """
    results: List[Dict[str, Any]] = []
    subj_count = len(gradebook.subjects)

    for s in gradebook.students:
        scores: List[float] = []
        for subj in gradebook.subjects:
            val = s.get_score(subj)
            try:
                v = float(val) if val is not None else 0.0
            except (TypeError, ValueError):
                # 비수치 입력은 0.0으로 처리
                v = 0.0
            scores.append(v)

        total = sum(scores)
        avg = (total / subj_count) if subj_count > 0 else 0.0
        grade = grade_from_avg(avg)

        results.append(
            {
                "student": s,
                "total": total,
                "avg": avg,
                "grade": grade,
                "rank": None,
            }
        )

    # 석차 계산 (총점 내림차순, 동점 처리: 동일 총점 동일 석차)
    sorted_by_total = sorted(
        results, key=lambda x: x["total"], reverse=True
    )

    last_total = None
    last_rank = 0
    for idx, item in enumerate(sorted_by_total, start=1):
        if last_total is None or item["total"] != last_total:
            last_rank = idx
            last_total = item["total"]
        item["rank"] = last_rank

    # 원래 학생 순서대로 rank를 유지한 리스트 반환
    # student 객체가 해시 가능하지 않을 수 있으므로 id()를 키로 사용
    rank_map = {id(item["student"]): item["rank"] for item in sorted_by_total}
    for item in results:
        item["rank"] = rank_map.get(id(item["student"]), None)

    return results
