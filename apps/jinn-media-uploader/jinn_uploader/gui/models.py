"""Qt item models and delegates for the upload queue and the R2 object list."""

from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import QAbstractTableModel, QModelIndex, QSortFilterProxyModel, Qt, Signal
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import QApplication, QComboBox, QStyle, QStyledItemDelegate, QStyleOptionProgressBar

from ..jobs import JobManager
from ..keys import CATEGORY_LABELS, classify, format_bytes, format_duration, format_eta, format_rate
from ..r2client import ObjectInfo
from ..uploader import ACTIVE_STATES, REMOTE_LABELS, JobState, UploadJob
from . import theme

PROGRESS_ROLE = Qt.ItemDataRole.UserRole + 1
JOB_ROLE = Qt.ItemDataRole.UserRole + 2

CATEGORY_CHOICES = [("mv", "MV"), ("bgm", "BGM"), ("other", "その他")]

EDITABLE_STATES = {JobState.PENDING, JobState.READY, JobState.NEEDS_DECISION, JobState.FAILED, JobState.CANCELLED}


class QueueModel(QAbstractTableModel):
    HEADERS = ["ファイル", "種別", "保存先キー", "サイズ", "状態", "進捗", "速度", "残り時間", "公開URL", "詳細"]
    editError = Signal(str)

    def __init__(self, manager: JobManager):
        super().__init__()
        self.manager = manager
        self._rows: list[UploadJob] = []

    def refresh(self) -> None:
        with self.manager.lock:
            jobs = list(self.manager.jobs)
        if [id(j) for j in jobs] != [id(j) for j in self._rows]:
            self.beginResetModel()
            self._rows = jobs
            self.endResetModel()
        elif self._rows:
            self.dataChanged.emit(self.index(0, 0), self.index(len(self._rows) - 1, len(self.HEADERS) - 1))

    def job(self, row: int) -> UploadJob:
        return self._rows[row]

    def rowCount(self, parent=QModelIndex()):  # noqa: N802
        return 0 if parent.isValid() else len(self._rows)

    def columnCount(self, parent=QModelIndex()):  # noqa: N802
        return 0 if parent.isValid() else len(self.HEADERS)

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):  # noqa: N802
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return self.HEADERS[section]
        return None

    def flags(self, index):
        base = Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
        if index.column() in (1, 2) and self._rows[index.row()].state in EDITABLE_STATES:
            base |= Qt.ItemFlag.ItemIsEditable
        return base

    @staticmethod
    def status_text(job: UploadJob) -> str:
        s = job.state.value
        if job.state in (JobState.READY, JobState.NEEDS_DECISION) and job.remote not in ("unknown", "new"):
            s += f"（{REMOTE_LABELS.get(job.remote, job.remote)}）"
        if job.state == JobState.READY and job.decision == "overwrite":
            s += "（上書き）"
        if job.resumed and job.state in (JobState.UPLOADING, JobState.DONE):
            s += "（再開）"
        return s

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        job = self._rows[index.row()]
        col = index.column()
        if role == JOB_ROLE:
            return job
        if role == PROGRESS_ROLE and col == 5:
            if job.state in (JobState.SKIPPED, JobState.CANCELLED):
                return None
            return 1000 if job.state == JobState.DONE else int(job.fraction * 1000)
        if role in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole):
            if col == 0:
                return job.name
            if col == 1:
                return job.category if role == Qt.ItemDataRole.EditRole else CATEGORY_LABELS.get(job.category, job.category)
            if col == 2:
                return job.key
            if col == 3:
                return format_bytes(job.total)
            if col == 4:
                return self.status_text(job)
            if col == 5:
                return ""
            if col == 6:
                return format_rate(job.rate()) if job.state == JobState.UPLOADING else ""
            if col == 7:
                return format_eta(job.eta()) if job.state == JobState.UPLOADING else ""
            if col == 8:
                return job.public_url
            if col == 9:
                detail = job.message or job.error
                if job.duplicates and job.state == JobState.NEEDS_DECISION:
                    detail = (detail + " " if detail else "") + "重複: " + ", ".join(job.duplicates)
                if job.media and job.media.duration and not detail:
                    w, h = job.media.display_size
                    detail = f"{format_duration(job.media.duration)}" + (f" / {w}×{h}" if w else "")
                return detail
        if role == Qt.ItemDataRole.ToolTipRole:
            if col == 0:
                return str(job.path)
            if col == 9:
                return job.error or job.message
            if col == 8:
                return job.public_url or None
            if col == 2:
                return "ダブルクリックで保存先キーを編集できます" if job.state in EDITABLE_STATES else job.key
        if role == Qt.ItemDataRole.ForegroundRole and col == 4:
            color = theme.STATE_COLORS.get(job.state.value)
            if job.state in ACTIVE_STATES:
                color = theme.ACCENT_2
            return QBrush(QColor(color)) if color else None
        if role == Qt.ItemDataRole.TextAlignmentRole and col in (3, 6, 7):
            return int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        return None

    def setData(self, index, value, role=Qt.ItemDataRole.EditRole):  # noqa: N802
        if role != Qt.ItemDataRole.EditRole or not index.isValid():
            return False
        job = self._rows[index.row()]
        try:
            if index.column() == 1:
                self.manager.set_category(job, str(value))
            elif index.column() == 2:
                text = str(value).strip()
                if text and text != job.key:
                    self.manager.set_key(job, text)
            else:
                return False
        except ValueError as exc:
            self.editError.emit(str(exc))
            return False
        self.dataChanged.emit(self.index(index.row(), 0), self.index(index.row(), len(self.HEADERS) - 1))
        return True


class ProgressDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        value = index.data(PROGRESS_ROLE)
        if value is None:
            super().paint(painter, option, index)
            return
        opt = QStyleOptionProgressBar()
        opt.rect = option.rect.adjusted(4, 6, -4, -6)
        opt.minimum = 0
        opt.maximum = 1000
        opt.progress = int(value)
        opt.text = f"{value / 10:.1f}%"
        opt.textVisible = True
        opt.state = QStyle.StateFlag.State_Enabled | QStyle.StateFlag.State_Horizontal
        style = option.widget.style() if option.widget else QApplication.style()
        style.drawControl(QStyle.ControlElement.CE_ProgressBar, opt, painter, option.widget)


class CategoryDelegate(QStyledItemDelegate):
    def createEditor(self, parent, option, index):  # noqa: N802
        cb = QComboBox(parent)
        for key, label in CATEGORY_CHOICES:
            cb.addItem(label, key)
        return cb

    def setEditorData(self, editor, index):  # noqa: N802
        i = editor.findData(index.data(Qt.ItemDataRole.EditRole))
        editor.setCurrentIndex(max(0, i))

    def setModelData(self, editor, model, index):  # noqa: N802
        model.setData(index, editor.currentData(), Qt.ItemDataRole.EditRole)


class ObjectsModel(QAbstractTableModel):
    HEADERS = ["キー", "サイズ", "更新日時", "種別", "公開URL"]

    def __init__(self, url_for):
        super().__init__()
        self._rows: list[ObjectInfo] = []
        self._url_for = url_for

    def set_objects(self, objects: list[ObjectInfo]) -> None:
        self.beginResetModel()
        self._rows = sorted(objects, key=lambda o: o.last_modified or datetime.min, reverse=True)
        self.endResetModel()

    def object(self, row: int) -> ObjectInfo:
        return self._rows[row]

    def rowCount(self, parent=QModelIndex()):  # noqa: N802
        return 0 if parent.isValid() else len(self._rows)

    def columnCount(self, parent=QModelIndex()):  # noqa: N802
        return 0 if parent.isValid() else len(self.HEADERS)

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):  # noqa: N802
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return self.HEADERS[section]
        return None

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        o = self._rows[index.row()]
        col = index.column()
        if role == Qt.ItemDataRole.DisplayRole:
            if col == 0:
                return o.key
            if col == 1:
                return format_bytes(o.size)
            if col == 2:
                return o.last_modified.astimezone().strftime("%Y-%m-%d %H:%M") if o.last_modified else ""
            if col == 3:
                return CATEGORY_LABELS.get(classify(o.key), "") if not o.key.endswith((".jpg", ".webp", ".png")) else "画像"
            if col == 4:
                return self._url_for(o.key)
        if role == Qt.ItemDataRole.UserRole:  # sort keys
            if col == 1:
                return o.size
            if col == 2:
                return o.last_modified.timestamp() if o.last_modified else 0
            return self.data(index, Qt.ItemDataRole.DisplayRole)
        if role == Qt.ItemDataRole.TextAlignmentRole and col == 1:
            return int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        if role == Qt.ItemDataRole.ToolTipRole and col in (0, 4):
            return self.data(index, Qt.ItemDataRole.DisplayRole)
        return None


class ObjectsFilter(QSortFilterProxyModel):
    def __init__(self):
        super().__init__()
        self.prefix = ""
        self.text = ""
        self.setSortRole(Qt.ItemDataRole.UserRole)

    def set_filter(self, prefix: str, text: str) -> None:
        self.prefix = prefix
        self.text = text.lower().strip()
        self.invalidateFilter()

    def filterAcceptsRow(self, row, parent):  # noqa: N802
        o = self.sourceModel().object(row)
        if self.prefix and not o.key.startswith(self.prefix):
            return False
        return not self.text or self.text in o.key.lower()
