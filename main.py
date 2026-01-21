import sys
from PyQt6.QtWidgets import (
    QApplication,
    QWidget,
    QLabel,
    QLineEdit,
    QPushButton,
    QFileDialog,
    QGridLayout,
    QMessageBox,
)
from ui_actions import convert, convert_tim_png


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TIM ↔ PNG Converter")
        self.resize(600, 150)
        self._build_ui()

    def _build_ui(self):
        layout = QGridLayout()

        # Folder A
        layout.addWidget(QLabel("Pure Source Folder (TIM):"), 0, 0)
        self.edit_a = QLineEdit()
        layout.addWidget(self.edit_a, 0, 1)
        btn_a = QPushButton("Browse")
        btn_a.clicked.connect(self.source_folder_select)
        layout.addWidget(btn_a, 0, 2)

        # Folder B
        layout.addWidget(QLabel("WIP Folder (PNG):"), 1, 0)
        self.edit_b = QLineEdit()
        layout.addWidget(self.edit_b, 1, 1)
        btn_b = QPushButton("Browse")
        btn_b.clicked.connect(self.work_folder_select)
        layout.addWidget(btn_b, 1, 2)

        # Convert to PNG
        self.btn_convert = QPushButton("Convert source to WIP-PNG")
        self.btn_convert.clicked.connect(self.source_convert)
        layout.addWidget(self.btn_convert, 2, 1)

        # Output
        layout.addWidget(QLabel("Output folder:"), 3, 0)
        self.edit_out = QLineEdit()
        layout.addWidget(self.edit_out, 3, 1)
        btn_out = QPushButton("Browse")
        btn_out.clicked.connect(self.output_folder_select)
        layout.addWidget(btn_out, 3, 2)

        # Convert
        self.btn_convert = QPushButton("Convert")
        self.btn_convert.clicked.connect(self.final_convert)
        layout.addWidget(self.btn_convert, 4, 1)

        self.setLayout(layout)

    # -------------------- callbacks --------------------

    def source_folder_select(self):
        folder = QFileDialog.getExistingDirectory(self, "Select source files location (TIM)")
        if folder:
            self.edit_a.setText(folder)

    def work_folder_select(self):
        folder = QFileDialog.getExistingDirectory(self, "Select project folder (PNG)")
        if folder:
            self.edit_b.setText(folder)

    def output_folder_select(self):
        folder = QFileDialog.getExistingDirectory(self, "Select project output (TIM)")
        if folder:
            self.edit_out.setText(folder)



    def source_convert(self):
        source_folder = self.edit_a.text().strip()
        work_folder = self.edit_b.text().strip()

        if not source_folder or not work_folder:
            QMessageBox.warning(self, "Missing data", "Please select source and WIP folders.")
            return

        try:
            convert_tim_png(source_folder, work_folder)
            QMessageBox.information(self, "Done", "Conversion finished.")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def final_convert(self):
        source_folder = self.edit_a.text().strip()
        work_folder = self.edit_b.text().strip()
        output_folder = self.edit_out.text().strip()

        if not source_folder or not work_folder or not output_folder:
            QMessageBox.warning(self, "Missing data", "Please select all folders.")
            return

        try:
            convert(source_folder, work_folder, output_folder)
            QMessageBox.information(self, "Done", "Conversion finished.")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

# -------------------- entry point --------------------

def main():
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
