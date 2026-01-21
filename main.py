#!/usr/bin/env python3
# main.py - PyQt6 GUI z zapamiętywaniem ostatnich folderów w config.ini
# Poprawiona obsługa pliku config.ini dla środowisk "frozen" (PyInstaller)
# oraz podstawowa walidacja i lepsze komunikaty błędów.

from __future__ import annotations

import sys
import configparser
import traceback
from pathlib import Path
from typing import Optional

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

# Funkcje konwersji (lokalny moduł w tym samym katalogu projektu)
from ui_actions import convert_png_tim, convert_tim_png

CONFIG_SECTION = "last_paths"


def get_config_path() -> Path:
    """
    Zwraca ścieżkę do config.ini:
     - jeśli aplikacja jest spakowana przez PyInstaller (sys.frozen) -> obok pliku wykonywalnego
     - w trybie developerskim -> obok tego pliku źródłowego
    Dzięki temu config.ini jest trwały po spakowaniu aplikacji.
    """
    if getattr(sys, "frozen", False):
        base_dir = Path(sys.executable).parent
    else:
        base_dir = Path(__file__).parent
    return base_dir / "config.ini"


CONFIG_PATH: Path = get_config_path()


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TIM ↔ PNG Converter")
        self.resize(600, 160)
        self._build_ui()
        self._load_config()

    def _build_ui(self) -> None:
        layout = QGridLayout()

        # Folder A (TIM)
        layout.addWidget(QLabel("Pure Source Folder (TIM):"), 0, 0)
        self.edit_a = QLineEdit()
        layout.addWidget(self.edit_a, 0, 1)
        btn_a = QPushButton("Browse")
        btn_a.clicked.connect(self.source_folder_select)
        layout.addWidget(btn_a, 0, 2)

        # Folder B (PNG WIP)
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

        # Output (TIM)
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

    def _load_config(self) -> None:
        """Wczytaj config.ini (jeśli istnieje) i ustaw pola."""
        config = configparser.ConfigParser()
        try:
            if CONFIG_PATH.exists():
                config.read(CONFIG_PATH, encoding="utf-8")
                if CONFIG_SECTION in config:
                    sec = config[CONFIG_SECTION]
                    a = sec.get("source_folder", "").strip()
                    b = sec.get("work_folder", "").strip()
                    out = sec.get("output_folder", "").strip()
                    if a:
                        self.edit_a.setText(a)
                    if b:
                        self.edit_b.setText(b)
                    if out:
                        self.edit_out.setText(out)
        except Exception as e:
            # Nie przerywamy uruchomienia UI, ale logujemy stacktrace
            print(f"Warning: nie mogłem wczytać config.ini: {e}")
            traceback.print_exc()

    def _save_config(self) -> None:
        """Zapisz aktualne wartości pól do config.ini."""
        config = configparser.ConfigParser()
        config[CONFIG_SECTION] = {
            "source_folder": self.edit_a.text().strip(),
            "work_folder": self.edit_b.text().strip(),
            "output_folder": self.edit_out.text().strip(),
        }
        try:
            # upewnij się, że katalog docelowy istnieje (dla trybu frozen może być wymagane)
            CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                config.write(f)
        except Exception as e:
            print(f"Warning: nie mogłem zapisać config.ini: {e}")
            traceback.print_exc()

    # -------------------- callbacks --------------------

    def source_folder_select(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Select source files location (TIM)")
        if folder:
            self.edit_a.setText(str(folder))
            self._save_config()

    def work_folder_select(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Select project folder (PNG)")
        if folder:
            self.edit_b.setText(str(folder))
            self._save_config()

    def output_folder_select(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Select project output (TIM)")
        if folder:
            self.edit_out.setText(str(folder))
            self._save_config()

    # Konwersja surowego TIM do PNG - możliwych do edycji
    def source_convert(self) -> None:
        source_folder = self.edit_a.text().strip()
        work_folder = self.edit_b.text().strip()

        if not source_folder or not work_folder:
            QMessageBox.warning(self, "Brak danych", "Wybierz folder źródłowy (TIM) i WIP (PNG).")
            return

        if not Path(source_folder).is_dir() or not Path(work_folder).is_dir():
            QMessageBox.warning(self, "Błędne ścieżki", "Podane foldery nie istnieją lub są nieprawidłowe.")
            return

        try:
            convert_tim_png(source_folder, work_folder)
            self._save_config()
            QMessageBox.information(self, "Zakończono", "Konwersja TIM → PNG zakończona.")
        except Exception as e:
            traceback.print_exc()
            QMessageBox.critical(self, "Błąd", f"Wystąpił błąd:\n{e}")

    # Konwersja roboczego PNG spowrotem do TIM
    def final_convert(self) -> None:
        source_folder = self.edit_a.text().strip()
        work_folder = self.edit_b.text().strip()
        output_folder = self.edit_out.text().strip()

        if not source_folder or not work_folder or not output_folder:
            QMessageBox.warning(self, "Brak danych", "Wybierz wszystkie foldery (source, WIP, output).")
            return

        if not Path(source_folder).is_dir() or not Path(work_folder).is_dir():
            QMessageBox.warning(self, "Błędne ścieżki", "Source lub WIP folder nie istnieje lub jest nieprawidłowy.")
            return

        try:
            # upewnij się że folder output istnieje (stwórz jeśli nie)
            Path(output_folder).mkdir(parents=True, exist_ok=True)
            convert_png_tim(source_folder, work_folder, output_folder)
            self._save_config()
            QMessageBox.information(self, "Zakończono", "Konwersja PNG → TIM zakończona.")
        except Exception as e:
            traceback.print_exc()
            QMessageBox.critical(self, "Błąd", f"Wystąpił błąd:\n{e}")

    def closeEvent(self, event) -> None:
        """Zapisz config przy zamknięciu okna."""
        try:
            self._save_config()
        except Exception:
            pass
        super().closeEvent(event)


# -------------------- entry point --------------------

def main(argv: Optional[list[str]] = None) -> None:
    if argv is None:
        argv = sys.argv
    app = QApplication(argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
