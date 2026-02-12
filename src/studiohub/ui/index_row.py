from PySide6 import QtWidgets, QtCore


class IndexRow(QtWidgets.QFrame):
    def __init__(
        self,
        *,
        archive_added: int,
        studio_added: int,
        timestamp: str,
        parent=None,
    ):
        super().__init__(parent)

        self.setObjectName("IndexRow")
        self.setProperty("role", "index-row")

        self.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Fixed,
        )

        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(8, 6, 8, 6)
        root.setSpacing(2)

        # ---------------- Top line ----------------
        top = QtWidgets.QHBoxLayout()
        top.setSpacing(8)

        lbl_title = QtWidgets.QLabel("Inventory Updated")
        lbl_title.setProperty("role", "index-title")

        lbl_time = QtWidgets.QLabel(timestamp)
        lbl_time.setProperty("role", "index-time")
        lbl_time.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        top.addWidget(lbl_title, 1)
        top.addWidget(lbl_time, 0)

        # ---------------- Bottom line ----------------
        bottom = QtWidgets.QHBoxLayout()
        bottom.setSpacing(12)

        lbl_archive = QtWidgets.QLabel(f"archive: +{archive_added}")
        lbl_archive.setProperty("role", "index-detail")

        lbl_studio = QtWidgets.QLabel(f"Studio: +{studio_added}")
        lbl_studio.setProperty("role", "index-detail")

        bottom.addWidget(lbl_archive)
        bottom.addWidget(lbl_studio)
        bottom.addStretch(1)

        root.addLayout(top)
        root.addLayout(bottom)
