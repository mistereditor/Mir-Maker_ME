"""
ui_actions.py

Funkcje wywoływane przez UI.
Brak zależności od PyQt – czysta logika.
"""

import os
from pathlib import Path
from typing import Dict, List, Tuple

from tim_operations import read_tim, Tim_Object


# ============================================================
# 1. Wczytanie i mapowanie plików TIM (Folder A)
# ============================================================

def load_tim_files(folder_a: str) -> Dict[str, Tim_Object]:
    """
    Wczytuje wszystkie pliki .tim z folderu A
    Zwraca dict:
        key   = nazwa pliku bez rozszerzenia
        value = Tim_Object
    """
    tim_objects = {}

    folder = Path(folder_a)
    if not folder.is_dir():
        raise RuntimeError(f"Folder A nie istnieje: {folder_a}")

    for file in folder.iterdir():
        if file.suffix.lower() != ".tim":
            continue

        tim_data = read_tim(str(file))
        tim_obj = Tim_Object(tim_data)

        key = file.stem
        if key in tim_objects:
            raise RuntimeError(f"Duplikat nazwy TIM: {key}")

        tim_objects[key] = tim_obj

    if not tim_objects:
        raise RuntimeError("Folder A nie zawiera plików .tim")

    return tim_objects


# ============================================================
# 2. Wczytanie PNG i sprawdzenie zgodności rozmiarów (Folder B)
# ============================================================

def match_png_files(
    tim_objects: Dict[str, Tim_Object],
    folder_b: str
) -> Dict[str, str]:
    """
    Dopasowuje PNG do TIM po nazwie.
    Sprawdza:
      - czy PNG istnieje
      - czy ma taki sam rozmiar jak TIM

    Zwraca:
        key   = nazwa bazowa
        value = ścieżka do PNG
    """
    png_map = {}
    folder = Path(folder_b)

    if not folder.is_dir():
        raise RuntimeError(f"Folder B nie istnieje: {folder_b}")

    for name, tim in tim_objects.items():
        png_path = folder / f"{name}.png"

        if not png_path.exists():
            raise RuntimeError(f"Brak PNG dla {name}.tim")

        # sprawdzenie rozmiaru
        from PIL import Image
        with Image.open(png_path) as img:
            if img.size != (tim.pixel_data_width, tim.pixel_data_height):
                raise RuntimeError(
                    f"Rozmiar PNG niezgodny z TIM dla {name}: "
                    f"PNG={img.size}, TIM=({tim.pixel_data_width},{tim.pixel_data_height})"
                )

        png_map[name] = str(png_path)

    return png_map


# ============================================================
# 3. Grupowanie TIM po CLUT coords
# ============================================================

def group_by_clut_coords(
    tim_objects: Dict[str, Tim_Object]
) -> Dict[Tuple[bytes, int, int], List[str]]:
    """
    Grupuje TIM-y według:
        (format_flag, clut_coord_x, clut_coord_y)

    Zwraca:
        key   = (format_flag, x, y)
        value = lista nazw bazowych plików
    """
    groups = {}

    for name, tim in tim_objects.items():
        key = (tim.format_flag, tim.clut_coord_x, tim.clut_coord_y)
        groups.setdefault(key, []).append(name)

    return groups


# ============================================================
# 4. Walidacja palet w grupach (logika kluczowa!)
# ============================================================

def validate_group_palettes(
    groups: Dict[Tuple[bytes, int, int], List[str]],
    png_map: Dict[str, str]
):
    """
    Na tym etapie:
    - NIE kwantyzujemy jeszcze
    - tylko sprawdzamy spójność danych wejściowych

    Docelowo:
    - w każdej grupie będzie JEDNA wspólna paleta
    """
    for key, names in groups.items():
        if len(names) < 2:
            continue  # pojedynczy TIM – brak konfliktów

        # Na razie tylko informacja diagnostyczna
        # (później tu wejdzie analiza kolorów PNG)
        print(f"Grupa CLUT {key}: {len(names)} plików")
        for name in names:
            print(f"  - {name}.png")


# ============================================================
# 5. Główna funkcja wywoływana przez UI
# ============================================================

def convert_tim_png(folder_a: str, work_folder: str):
    """
    Wczytaj wszystkie TIMy z folder_a i zapisz jako PNGy do work_folder
    o tych samych nazwach (basename.png). Zwraca listę zapisanych plików.
    """
    from PIL import Image

    tim_objects = load_tim_files(folder_a)  # wykorzystuje istniejącą funkcję
    out_dir = Path(work_folder)
    out_dir.mkdir(parents=True, exist_ok=True)

    saved = []
    for name, tim in tim_objects.items():
        try:
            # upewnij się, że mamy PIL image w obiekcie Tim_Object
            pil_img = getattr(tim, "pil_image", None)
            if pil_img is None:
                # decode() ustawi tim.pil_image i zwróci QPixmap (ale potrzebujemy pil_image)
                # jeśli decode() nie istnieje / zachowuje się inaczej, rzućmy czytelny błąd
                if hasattr(tim, "decode"):
                    tim.decode()
                    pil_img = getattr(tim, "pil_image", None)
                else:
                    raise RuntimeError("Tim_Object nie ma metody decode()")

            if pil_img is None:
                raise RuntimeError(f"Nie udało się uzyskać obrazu PIL dla {name}")

            out_path = out_dir / (name + ".png")
            # Upewnij się, że zapisujemy PIL Image (RGBA) jako PNG
            if isinstance(pil_img, Image.Image):
                pil_img.save(out_path, "PNG")
            else:
                # jeśli pil_img jest QImage/QPixmap (nie powinno się zdarzyć w obecnej implementacji),
                # spróbujmy skonwertować przez bytes (rzadki kod ścieżki)
                raise RuntimeError(f"Obiekt pil_image dla {name} nie jest PIL.Image (typ={type(pil_img)})")

            saved.append(str(out_path))
        except Exception as e:
            # przerwij i zgłoś błąd — zgodnie z Twoim wymaganiem, żeby zatrzymać przy niezgodnościach
            raise RuntimeError(f"Failed to export TIM -> PNG for '{name}': {e}") from e

    # opcjonalnie zwróć listę zapisanych plików
    return saved



def convert_png_tim(folder_a: str, folder_b: str, out_folder: str):

    print("Loading TIM files...")
    tim_objects = load_tim_files(folder_a)

    print("Matching PNG files...")
    png_map = match_png_files(tim_objects, folder_b)

    print("Grouping by CLUT coords...")
    groups = group_by_clut_coords(tim_objects)

    print("Validating groups...")
    validate_group_palettes(groups, png_map)

    print("READY FOR QUANTIZATION & EXPORT")


