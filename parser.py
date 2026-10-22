import sys
import os
import pymupdf
import zxingcpp
from PIL import Image

def format_to_true_gs1(raw_text: str) -> str:
    """
    Преобразует строку вида (01)046809...(21)abc(91)EE12(92)xyz
    в чистый формат GS1 DataMatrix для 1С: 01046809...21abc<GS>91EE12<GS>92xyz
    Если скобок нет — возвращает как есть.
    Применяется ТОЛЬКО к DataMatrix при отсутствии флага -nogs.
    """
    text = raw_text.strip()
    if not text:
        return text

    if "(01)" not in text and "(21)" not in text:
        return text

    if text.startswith("(01)"):
        text = "01" + text[4:]

    text = text.replace("(21)", "21")
    text = text.replace("(91)", "\x1d91")
    text = text.replace("(92)", "\x1d92")

    return text

def save_as_txt(path, codes):
    """Записывает коды по одному на строку (CRLF), без заголовка и колонок."""
    with open(path, mode="wb") as f:
        for code in codes:
            line_bytes = (code + "\r\n").encode("utf-8")
            f.write(line_bytes)

def main():
    print(">>> PDF Barcode Parser v1.0.2 (build 2026-10-21) <<<")
    # Ожидаем: parser.py <PDF> <OUTPUT> [DPI] [-nogs]
    if len(sys.argv) < 3:
        print("Ошибка: Недостаточно аргументов.")
        print("Использование: python parser.py <PDF> <OUTPUT_FILE> [DPI] [-nogs]")
        print("DPI — необязательное число (по умолчанию 300).")
        print("-nogs — флаг: не применять GS1-форматирование к DataMatrix.")
        sys.exit(1)

    pdf_path = sys.argv[1]
    output_path = sys.argv[2]

    dpi = 300
    skip_gs_format = False

    i = 3
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg == "-nogs":
            skip_gs_format = True
        else:
            try:
                dpi = int(arg)
                if dpi <= 0:
                    raise ValueError
            except ValueError:
                print(f"Ошибка: некорректный аргумент '{arg}'. Ожидается число (DPI) или флаг '-nogs'.")
                sys.exit(1)
        i += 1

    if not os.path.exists(pdf_path):
        print(f"Ошибка: Файл PDF не найден: {pdf_path}")
        sys.exit(1)

    try:
        doc = pymupdf.open(pdf_path)
        total_pages = len(doc)
        extracted_codes = []
        missing_pages = []

        zoom = dpi / 72.0
        mat = pymupdf.Matrix(zoom, zoom)

        for page_num in range(total_pages):
            page = doc[page_num]
            pix = page.get_pixmap(matrix=mat)
            page_image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

            results = zxingcpp.read_barcodes(page_image)

            if not results:
                missing_pages.append(page_num + 1)
                continue

            for res in results:
                raw_code = res.text
                if not raw_code:
                    continue

                if not skip_gs_format and res.format == zxingcpp.BarcodeFormat.DataMatrix:
                    clean_code = format_to_true_gs1(raw_code)
                else:
                    clean_code = raw_code

                extracted_codes.append(clean_code)

        save_as_txt(output_path, extracted_codes)

        actual_count = len(extracted_codes)

        if missing_pages:
            print(f"Внимание: На страницах {missing_pages} коды не найдены.")
            print(f"Успешно. Найдено кодов: {actual_count}.")
            sys.exit(2)

        print(f"Успешно. Все страницы содержат коды. Найдено кодов: {actual_count}.")
        sys.exit(0)

    except Exception as e:
        print(f"Критическая ошибка: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
