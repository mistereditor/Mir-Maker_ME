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
        raise RuntimeError(f"Folder A does not exist: {folder_a}")

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
        raise RuntimeError("Source folder does not contain .tim files")

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
        raise RuntimeError(f"Work folder does not exist: {folder_b}")

    for name, tim in tim_objects.items():
        png_path = folder / f"{name}.png"

        if not png_path.exists():
            raise RuntimeError(f"No PNG for {name}.tim")

        # sprawdzenie rozmiaru
        from PIL import Image
        with Image.open(png_path) as img:
            if img.size != (tim.pixel_data_width, tim.pixel_data_height):
                raise RuntimeError(
                    f"Size of PNG not matching TIM for {name}: "
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



# na górze pliku ui_actions.py (jeśli jeszcze nie ma tych importów), dodaj:
from PIL import Image
from tim_operations import write_tim_file
import struct

# ---- helper: compute_group_palette (mozaika miniaturek + PIL.quantize MEDIANCUT) ----
def compute_group_palette(png_paths: List[str], palette_size: int) -> List[tuple]:
    """
    Z PNG-ów (ścieżki) buduje mozaikę miniaturek i kwantyzuje ją metodą MEDIANCUT,
    zwracając listę (r,g,b) długości palette_size.
    Deterministyczne i szybkie dla naszych celów.
    """
    thumbs = []
    max_thumb_dim = 128
    for p in png_paths:
        im = Image.open(p).convert("RGBA")
        w, h = im.size
        scale = min(1.0, max_thumb_dim / max(w, h))
        tw = max(1, int(w * scale))
        th = max(1, int(h * scale))
        thumbs.append(im.resize((tw, th), Image.Resampling.LANCZOS).convert("RGB"))
        im.close()

    # ułóż miniatury w wiersze o max szerokości ~1024px
    max_row_w = 1024
    rows = []
    cur_row = []
    cur_w = 0
    cur_h = 0
    for t in thumbs:
        tw, th = t.size
        if cur_row and (cur_w + tw > max_row_w):
            rows.append((cur_row, cur_h))
            cur_row = [t]
            cur_w = tw
            cur_h = th
        else:
            cur_row.append(t)
            cur_w += tw
            cur_h = max(cur_h, th)
    if cur_row:
        rows.append((cur_row, cur_h))

    mosaic_w = max(sum(img.size[0] for img in row[0]) for row in rows)
    mosaic_h = sum(row[1] for row in rows)
    mosaic = Image.new("RGB", (mosaic_w, mosaic_h), (0, 0, 0))
    y = 0
    for row, row_h in rows:
        x = 0
        for img in row:
            mosaic.paste(img, (x, y))
            x += img.size[0]
        y += row_h

    pal_img = mosaic.quantize(colors=palette_size, method=Image.MEDIANCUT)
    flat = pal_img.getpalette() or []
    palette = []
    for i in range(0, min(len(flat), palette_size * 3), 3):
        palette.append((flat[i], flat[i + 1], flat[i + 2]))
    if len(palette) < palette_size:
        palette += [(0, 0, 0)] * (palette_size - len(palette))
    return palette


# ---- główna funkcja: convert_png_tim ----
def convert_png_tim(folder_a: str, folder_b: str, out_folder: str):
    """
    Zamienia PNG (w folder_b) z powrotem w pliki .tim bazując na metadanych TIM z folder_a.
    Zwraca listę zapisanych plików (ścieżek) lub podnosi wyjątek przy błędzie.
    """
    # 1) wczytaj TIMy
    tim_objects = load_tim_files(folder_a)  # używa Tim_Object
    # 2) dopasuj PNGy (sprawdza istnienie i zgodność rozmiarów)
    png_map = match_png_files(tim_objects, folder_b)
    # 3) grupuj
    groups = group_by_clut_coords(tim_objects)

    out_path_dir = Path(out_folder)
    out_path_dir.mkdir(parents=True, exist_ok=True)

    saved = []

    # process groups
    for key, names in groups.items():
        fmt_flag, clut_x, clut_y = key
        palette_size = 16 if fmt_flag == b'\x08\x00\x00\x00' else 256

        # collect PNG paths for this group
        png_paths = [png_map[name] for name in names]

        # compute one palette for entire group
        group_palette = compute_group_palette(png_paths, palette_size)

        # For each name in group map & encode
        for name in names:
            tim_obj = tim_objects[name]  # Tim_Object
            png_file = png_map[name]

            # open PIL RGBA
            src = Image.open(png_file).convert("RGBA")
            # ensure size matches (match_png_files already checked, but double-check)
            if src.size != (tim_obj.pixel_data_width, tim_obj.pixel_data_height):
                raise RuntimeError(f"Size of PNG {png_file} != TIM {name} -> abort")

            # Try to use Tim_Object.encode_from_pil if available (preferred)
            try:
                out_dict = tim_obj.encode_from_pil(src, group_palette, transparent_threshold=128)
            except AttributeError:
                # fallback: ręczne mapowanie (nearest + pakowanie)
                # map pixels to palette (RGB)
                img_rgb = src.convert("RGB")
                pixels = list(img_rgb.getdata())
                # precompute palette array
                pal = group_palette

                def nearest_index(px):
                    pr, pg, pb = px
                    best_i = 0
                    br, bg, bb = pal[0]
                    best_d = (pr - br) ** 2 + (pg - bg) ** 2 + (pb - bb) ** 2
                    for i in range(1, len(pal)):
                        r, g, b = pal[i]
                        d = (pr - r) ** 2 + (pg - g) ** 2 + (pb - b) ** 2
                        if d < best_d:
                            best_d = d
                            best_i = i
                    return best_i

                indexes = [nearest_index(px) & 0xFF for px in pixels]
                # transparency
                alpha = src.split()[3]
                mask = [a < 128 for a in alpha.getdata()]
                for i, m in enumerate(mask):
                    if m:
                        indexes[i] = 0

                # build pixel bytes
                if fmt_flag == b'\x09\x00\x00\x00':  # 8bpp
                    pixel_bytes = bytes([int(v) & 0xFF for v in indexes])
                    stored_width_value = tim_obj.pixel_data_width // 2
                else:  # 4bpp
                    w = tim_obj.pixel_data_width
                    h = tim_obj.pixel_data_height
                    if w % 2 != 0:
                        raise RuntimeError(f"Width must be even for 4bpp (file {name})")
                    outb = bytearray()
                    for y in range(h):
                        row_start = y * w
                        for x in range(0, w, 2):
                            i1 = indexes[row_start + x] & 0x0F
                            i2 = indexes[row_start + x + 1] & 0x0F
                            outb.append((i2 << 4) | i1)
                    pixel_bytes = bytes(outb)
                    stored_width_value = tim_obj.pixel_data_width // 4

                # build clut bytes and pad to expected entries
                clut_expected = tim_obj.clut_size_x * tim_obj.clut_size_y
                if clut_expected == 0:
                    clut_expected = palette_size
                clut_bytes = bytearray()
                for (r, g, b) in group_palette:
                    val = ((r >> 3) & 0x1F) | (((g >> 3) & 0x1F) << 5) | (((b >> 3) & 0x1F) << 10)
                    clut_bytes += struct.pack("<H", val)
                # pad or trim
                if len(clut_bytes) < clut_expected * 2:
                    last = clut_bytes[-2:] if len(clut_bytes) >= 2 else struct.pack("<H", 0)
                    while len(clut_bytes) < clut_expected * 2:
                        clut_bytes += last
                elif len(clut_bytes) > clut_expected * 2:
                    clut_bytes = clut_bytes[:clut_expected * 2]

                new_clut_bnum = len(clut_bytes) + 12
                new_pixel_bnum = len(pixel_bytes) + 12

                out_dict = {
                    "header_id": tim_obj.header_id if hasattr(tim_obj, "header_id") else b'\x10\x00\x00\x00',
                    "tim_format": fmt_flag,
                    "new_clut_bnum": new_clut_bnum,
                    "clut_coord_x": tim_obj.clut_coord_x,
                    "clut_coord_y": tim_obj.clut_coord_y,
                    "clut_size_x": tim_obj.clut_size_x,
                    "clut_size_y": tim_obj.clut_size_y,
                    "common_clut": bytes(clut_bytes),
                    "new_pixel_bnum": new_pixel_bnum,
                    "pixel_coord_x": tim_obj.pixel_coord_x,
                    "pixel_coord_y": tim_obj.pixel_coord_y,
                    "stored_width_value": stored_width_value,
                    "height": tim_obj.pixel_data_height,
                    "new_pixel_data": pixel_bytes
                }

            # finally, write TIM
            out_filename = os.path.join(out_folder, name + ".tim")
            try:
                write_tim_file(out_dict, out_filename)
                saved.append(out_filename)
            except Exception as e:
                raise RuntimeError(f"Failed to write TIM for {name}: {e}") from e
            finally:
                src.close()

    return saved
