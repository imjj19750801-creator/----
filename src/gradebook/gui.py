# src/gradebook/gui.py
import logging

import pandas as pd
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QFont, QPainter
from PyQt5.QtPrintSupport import QPrintDialog, QPrinter
from PyQt5.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from .model import GradeBook

logger = logging.getLogger(__name__)

# 픽셀 기준 글자폭 대략값
PX_PER_CHAR = 12

# 열 너비 정의
COL_WIDTHS = {
    "이름": 8 * PX_PER_CHAR,
    "과목": 6 * PX_PER_CHAR,
    "총점": 6 * PX_PER_CHAR,
    "평균": 6 * PX_PER_CHAR,
    "등급": 4 * PX_PER_CHAR,
    "석차": 4 * PX_PER_CHAR,
    "전화번호": 12 * PX_PER_CHAR,
}

# 고정 꼬리 열들
FIXED_TAIL_HEADERS = [
    "총점",
    "평균",
    "등급",
    "석차",
    "전화번호",
    "비고",
]

# 줄무늬 색
ODD_ROW_COLOR = QColor(240, 240, 240)


def grade_from_avg(avg):
    if avg >= 90:
        return "A"
    if avg >= 80:
        return "B"
    if avg >= 70:
        return "C"
    if avg >= 60:
        return "D"
    return "F"


class GradeManager(QTableWidget):
    def __init__(self, parent=None):
        super().__init__(0, 0, parent)
        self.setAlternatingRowColors(True)
        self.setFont(QFont("맑은 고딕", 10))
        self.horizontalHeader().setFont(
            QFont("맑은 고딕", 10, QFont.Bold)
        )
        self.verticalHeader().setFont(QFont("맑은 고딕", 10))
        self.setStyleSheet(
            "QHeaderView::section { background-color: #e6e6e6; }"
        )
        self.horizontalHeader().setHighlightSections(False)
        self.verticalHeader().setDefaultAlignment(Qt.AlignCenter)
        self.setSelectionBehavior(QTableWidget.SelectItems)
        self.setSelectionMode(QTableWidget.SingleSelection)


class ChartWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        self.label = QLabel("차트 영역 (간단 표시)")
        self.label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.label)

    def plot_chart(self, chart_type):
        mapping = {
            "avg": "평균 점수",
            "rank": "석차 분포",
            "subject_avg": "과목별 평균",
            "grade_dist": "등급 분포",
            "total_line": "총점 선그래프",
        }
        title = mapping.get(chart_type, chart_type)
        self.label.setText(f"{title} 차트 표시 예정")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("성적 관리 프로그램")
        self.subjects = []
        self._in_calc = False
        self._dirty = False

        # 테이블 및 모델
        self.table = GradeManager(self)
        self.gradebook = GradeBook()

        self._refresh_headers()
        self.table.itemChanged.connect(self._on_item_changed)

        # 상단 버튼/입력
        add_student_btn = QPushButton("학생 추가")
        add_student_btn.clicked.connect(self.add_student)
        del_student_btn = QPushButton("학생 삭제")
        del_student_btn.clicked.connect(self.del_selected_student)

        self.subject_name_edit = QLineEdit()
        self.subject_name_edit.setMaxLength(10)
        self.subject_name_edit.setFixedWidth(120)

        add_subject_btn = QPushButton("과목 추가")
        add_subject_btn.clicked.connect(self.add_subject)
        del_subject_btn = QPushButton("과목 삭제")
        del_subject_btn.clicked.connect(self.del_subject)

        self.name_search_edit = QLineEdit()
        self.name_search_edit.setPlaceholderText("이름 검색")
        self.name_search_edit.textChanged.connect(self.apply_filters)

        self.min_avg_spin = QSpinBox()
        self.min_avg_spin.setRange(0, 100)
        self.min_avg_spin.setPrefix("평균 ≥ ")
        self.min_avg_spin.valueChanged.connect(self.apply_filters)

        save_btn = QPushButton("엑셀 저장")
        save_btn.clicked.connect(self.save_to_excel)
        load_btn = QPushButton("엑셀 불러오기")
        load_btn.clicked.connect(self.load_from_excel)
        print_btn = QPushButton("PDF 출력/인쇄")
        print_btn.clicked.connect(self.print_to_pdf_or_printer)

        # 탭
        self.tabs = QTabWidget()

        # 성적표 탭 레이아웃
        tab_scores = QWidget()
        top_layout = QHBoxLayout()
        top_layout.addWidget(add_student_btn)
        top_layout.addWidget(del_student_btn)
        top_layout.addSpacing(16)
        top_layout.addWidget(QLabel("과목:"))
        top_layout.addWidget(self.subject_name_edit)
        top_layout.addWidget(add_subject_btn)
        top_layout.addWidget(del_subject_btn)
        top_layout.addSpacing(16)
        top_layout.addWidget(self.name_search_edit)
        top_layout.addWidget(self.min_avg_spin)
        top_layout.addStretch(1)
        top_layout.addWidget(save_btn)
        top_layout.addWidget(load_btn)
        top_layout.addWidget(print_btn)

        layout_scores = QVBoxLayout(tab_scores)
        layout_scores.addLayout(top_layout)
        layout_scores.addWidget(self.table)
        self.tabs.addTab(tab_scores, "성적표")

        # 차트 탭 레이아웃
        tab_charts = QWidget()
        chart_btns = QHBoxLayout()
        chart_btns.setSpacing(10)
        chart_btns.setContentsMargins(10, 10, 10, 10)
        chart_list = [
            ("평균 점수", "avg"),
            ("석차 분포", "rank"),
            ("과목별 평균", "subject_avg"),
            ("등급 분포", "grade_dist"),
            ("총점 선그래프", "total_line"),
        ]
        for t in chart_list:
            b = QPushButton(t[0])
            b.clicked.connect(lambda _, tt=t[1]: self.chart_widget.plot_chart(tt))
            chart_btns.addWidget(b)

        layout_charts = QVBoxLayout(tab_charts)
        layout_charts.addLayout(chart_btns)
        self.chart_widget = ChartWidget(self)
        layout_charts.addWidget(self.chart_widget)
        self.tabs.addTab(tab_charts, "차트")

        # 메인 컨테이너
        container = QWidget()
        main_layout = QVBoxLayout(container)
        main_layout.addWidget(self.tabs)
        self.setCentralWidget(container)

        # 초기 데이터 예시
        self.add_subject_by_name("국어")
        self.add_subject_by_name("수학")
        self.add_student("홍길동")
        self.add_student("김철수")
        self.set_score(0, "국어", 95)
        self.set_score(0, "수학", 88)
        self.set_score(1, "국어", 90)
        self.set_score(1, "수학", 90)
        self.recalculate_all()

    def renumber_students(self):
        for r in range(self.table.rowCount()):
            self.table.setVerticalHeaderItem(
                r, QTableWidgetItem(str(r + 1))
            )
            for c in range(self.table.columnCount()):
                item = self.table.item(r, c)
                if item:
                    if (r % 2) == 0:
                        item.setBackground(ODD_ROW_COLOR)
                    else:
                        item.setBackground(Qt.white)

    def _fixed_start_col(self):
        return 1 + len(self.subjects)

    def _refresh_headers(self):
        headers = ["이름"] + self.subjects + FIXED_TAIL_HEADERS
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)

        for i, h in enumerate(headers):
            if h == "비고":
                self.table.horizontalHeader().setSectionResizeMode(
                    i, QHeaderView.Stretch
                )
            elif h == "전화번호":
                self.table.horizontalHeader().setSectionResizeMode(
                    i, QHeaderView.Fixed
                )
                self.table.setColumnWidth(
                    i, COL_WIDTHS["전화번호"]
                )
            elif h == "이름":
                self.table.horizontalHeader().setSectionResizeMode(
                    i, QHeaderView.Fixed
                )
                self.table.setColumnWidth(i, COL_WIDTHS["이름"])
            elif h in ["총점", "평균", "등급", "석차"]:
                self.table.horizontalHeader().setSectionResizeMode(
                    i, QHeaderView.Fixed
                )
                self.table.setColumnWidth(i, COL_WIDTHS[h])
            else:
                self.table.horizontalHeader().setSectionResizeMode(
                    i, QHeaderView.Fixed
                )
                self.table.setColumnWidth(i, COL_WIDTHS["과목"])

        for i in range(self.table.columnCount()):
            item = self.table.horizontalHeaderItem(i)
            if item:
                item.setTextAlignment(Qt.AlignCenter)

    def _on_item_changed(self, item):
        if self._in_calc:
            return
        self._dirty = True
        self.recalculate_all()

    def add_student(self, name=""):
        r = self.table.rowCount()
        self.table.insertRow(r)
        self.table.setItem(r, 0, QTableWidgetItem(name))
        for c in range(1, self.table.columnCount()):
            self.table.setItem(r, c, QTableWidgetItem(""))
        self.renumber_students()

    def del_selected_student(self):
        r = self.table.currentRow()
        if r >= 0:
            self.table.removeRow(r)
            self.renumber_students()
            self.recalculate_all()

    def add_subject(self):
        subj = self.subject_name_edit.text().strip()
        if subj and subj not in self.subjects:
            self.add_subject_by_name(subj)
            self.subject_name_edit.clear()

    def add_subject_by_name(self, subj):
        self.subjects.append(subj)
        self._refresh_headers()
        subj_col = 1 + len(self.subjects) - 1
        for r in range(self.table.rowCount()):
            self.table.setItem(r, subj_col, QTableWidgetItem(""))

    def del_subject(self):
        if self.subjects:
            self.subjects.pop()
            self._refresh_headers()
            self.recalculate_all()

    def set_score(self, row, subj, score):
        if subj in self.subjects:
            c = 1 + self.subjects.index(subj)
            self.table.setItem(row, c, QTableWidgetItem(str(score)))

    def recalculate_all(self):
        self._in_calc = True
        try:
            fixed_start = self._fixed_start_col()
            col_total = fixed_start + 0
            col_avg = fixed_start + 1
            col_grade = fixed_start + 2
            col_rank = fixed_start + 3

            totals = []
            for r in range(self.table.rowCount()):
                scores = []
                for s_idx, _subj in enumerate(self.subjects):
                    c = 1 + s_idx
                    item = self.table.item(r, c)
                    if item:
                        try:
                            v = float(item.text())
                            scores.append(v)
                        except (ValueError, TypeError):
                            # 잘못된 입력은 무시
                            logger.debug(
                                "비수치 입력 무시: row=%s col=%s",
                                r,
                                c,
                            )
                total = sum(scores) if scores else 0.0
                avg = (total / len(self.subjects)) if self.subjects else 0.0
                grade = grade_from_avg(avg)

                self.table.setItem(
                    r, col_total, QTableWidgetItem(f"{total:.0f}")
                )
                self.table.setItem(
                    r, col_avg, QTableWidgetItem(f"{avg:.1f}")
                )
                self.table.setItem(r, col_grade, QTableWidgetItem(grade))

                totals.append((r, total))

            totals_sorted = sorted(totals, key=lambda x: x[1], reverse=True)
            rank_map = {
                r_idx: rank + 1
                for rank, (r_idx, _) in enumerate(totals_sorted)
            }
            for r in range(self.table.rowCount()):
                rk = rank_map.get(r, "")
                self.table.setItem(r, col_rank, QTableWidgetItem(str(rk)))

            self.renumber_students()
        finally:
            self._in_calc = False

    def apply_filters(self):
        name_filter = self.name_search_edit.text().strip()
        min_avg = self.min_avg_spin.value()
        fixed_start = self._fixed_start_col()
        col_avg = fixed_start + 1
        for r in range(self.table.rowCount()):
            show = True
            if name_filter:
                name_item = self.table.item(r, 0)
                if not name_item or (name_filter not in name_item.text()):
                    show = False
            avg_item = self.table.item(r, col_avg)
            try:
                avg_val = float(avg_item.text())
                if avg_val < min_avg:
                    show = False
            except (AttributeError, ValueError, TypeError):
                # 비어있거나 비수치인 경우 필터에서 제외
                logger.debug("평균값 파싱 실패: row=%s", r)
            self.table.setRowHidden(r, not show)

    def save_to_excel(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "엑셀 저장", "", "Excel Files (*.xlsx)"
        )
        if not path:
            return
        headers = [
            self.table.horizontalHeaderItem(c).text()
            for c in range(self.table.columnCount())
        ]
        data = []
        for r in range(self.table.rowCount()):
            row = []
            for c in range(self.table.columnCount()):
                item = self.table.item(r, c)
                row.append(item.text() if item else "")
            data.append(row)
        df = pd.DataFrame(data, columns=headers)
        df.to_excel(path, index=False)

    def load_from_excel(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "엑셀 불러오기", "", "Excel Files (*.xlsx)"
        )
        if not path:
            return
        df = pd.read_excel(path)
        self.subjects = [
            c for c in df.columns
            if c not in ["이름"] + FIXED_TAIL_HEADERS
        ]
        self._refresh_headers()
        self.table.setRowCount(0)
        for _, row in df.iterrows():
            r = self.table.rowCount()
            self.table.insertRow(r)
            for c, val in enumerate(row):
                self.table.setItem(r, c, QTableWidgetItem(str(val)))
        self.renumber_students()
        self.recalculate_all()

    def print_to_pdf_or_printer(self):
        printer = QPrinter(QPrinter.HighResolution)
        dialog = QPrintDialog(printer, self)
        if dialog.exec_() == QPrintDialog.Accepted:
            painter = QPainter(printer)
            self.table.render(painter)
            painter.end()

    def closeEvent(self, event):
        if self._dirty:
            reply = QMessageBox.question(
                self,
                "종료 확인",
                "변경사항을 저장하지 않았습니다. 종료하시겠습니까?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if reply == QMessageBox.No:
                event.ignore()
                return
        event.accept()
