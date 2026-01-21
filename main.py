#!/usr/bin/env python3
# main.py - PyQt6 GUI z zapamiętywaniem ostatnich folderów w config.ini

import sys
import configparser
from pathlib import Path
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
from ui_actions import convert_png_tim, convert_tim_png

# config file obok tego skryptu
CONFIG_PATH = Path(__file__).parent / "config.ini"
CONFIG_SECTION = "last_paths"


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TIM ↔ PNG Converter")
        self.resize(600, 150)
        self._build_ui()
        # load config after UI built
        self._load_config()

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
        self.btn_convert_to_png = QPushButton("Convert source to WIP-PNG")
        self.btn_convert_to_png.clicked.connect(self.source_convert)
        layout.addWidget(self.btn_convert_to_png, 2, 1)

        # Output
        layout.addWidget(QLabel("Output folder:"), 3, 0)
        self.edit_out = QLineEdit()
        layout.addWidget(self.edit_out, 3, 1)
        btn_out = QPushButton("Browse")
        btn_out.clicked.connect(self.output_folder_select)
        layout.addWidget(btn_out, 3, 2)

        # Convert final
        self.btn_convert_final = QPushButton("Convert")
        self.btn_convert_final.clicked.connect(self.final_convert)
        layout.addWidget(self.btn_convert_final, 4, 1)

        self.setLayout(layout)

    # -------------------- config handling --------------------

    def _load_config(self):
        """Wczytaj config.ini (jeśli istnieje) i ustaw pola."""
        config = configparser.ConfigParser()
        if CONFIG_PATH.exists():
            try:
                config.read(CONFIG_PATH, encoding="utf-8")
                if CONFIG_SECTION in config:
                    sec = config[CONFIG_SECTION]
                    a = sec.get("source_folder", "")
                    b = sec.get("work_folder", "")
                    out = sec.get("output_folder", "")
                    if a:
                        self.edit_a.setText(a)
                    if b:
                        self.edit_b.setText(b)
                    if out:
                        self.edit_out.setText(out)
            except Exception as e:
                # nie przerywamy uruchomienia UI, tylko pokazujemy info w konsoli
                print(f"Warning: nie mogłem wczytać config.ini: {e}")

    def _save_config(self):
        """Zapisz aktualne wartości pól do config.ini."""
        config = configparser.ConfigParser()
        config[CONFIG_SECTION] = {
            "source_folder": self.edit_a.text().strip(),
            "work_folder": self.edit_b.text().strip(),
            "output_folder": self.edit_out.text().strip()
        }
        try:
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                config.write(f)
        except Exception as e:
            print(f"Warning: nie mogłem zapisać config.ini: {e}")

    # -------------------- callbacks --------------------

    def source_folder_select(self):
        folder = QFileDialog.getExistingDirectory(self, "Select source files location (TIM)")
        if folder:
            self.edit_a.setText(folder)
            self._save_config()

    def work_folder_select(self):
        folder = QFileDialog.getExistingDirectory(self, "Select project folder (PNG)")
        if folder:
            self.edit_b.setText(folder)
            self._save_config()

    def output_folder_select(self):
        folder = QFileDialog.getExistingDirectory(self, "Select project output (TIM)")
        if folder:
            self.edit_out.setText(folder)
            self._save_config()

    # Konwersja surowego TIM do PNG - możliwych do edycji
    def source_convert(self):
        source_folder = self.edit_a.text().strip()
        work_folder = self.edit_b.text().strip()

        if not source_folder or not work_folder:
            QMessageBox.warning(self, "Missing data", "Please select source and WIP folders.")
            return

        try:
            convert_tim_png(source_folder, work_folder)
            # zapisz config po powodzeniu
            self._save_config()
            QMessageBox.information(self, "Done", "Conversion finished.")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    # Konwersja roboczego PNG spowrotem do TIM
    def final_convert(self):
        source_folder = self.edit_a.text().strip()
        work_folder = self.edit_b.text().strip()
        output_folder = self.edit_out.text().strip()

        if not source_folder or not work_folder or not output_folder:
            QMessageBox.warning(self, "Missing data", "Please select all folders.")
            return

        try:
            convert_png_tim(source_folder, work_folder, output_folder)
            # zapisz config po powodzeniu
            self._save_config()
            QMessageBox.information(self, "Done", "Conversion finished.")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    # save config on close as well
    def closeEvent(self, event):
        try:
            self._save_config()
        except Exception:
            pass
        super().closeEvent(event)


# -------------------- entry point --------------------

def main():
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
