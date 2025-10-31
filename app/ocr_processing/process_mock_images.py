from pathlib import Path
import json
from typing import Any, Dict, Union, List, cast
from pdf2image import convert_from_path  # type: ignore
from PIL import Image
from . import ocr

OCRResult = Dict[str, Union[str, Dict[str, Any]]]


def process_all(input_dir: str = "mock_images") -> Dict[str, OCRResult]:
    p: Path = Path(input_dir)
    results: Dict[str, OCRResult] = {}
    if not p.exists():
        print(f"Diretório de entrada não encontrado: {input_dir}")
        return results

    supported_img_suffixes = (".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff")
    supported_pdf_suffixes = (".pdf",)
    for f in sorted(p.iterdir()):
        if not f.is_file():
            continue

        file_path: str = str(f)
        file_name: str = f.name
        temp_img: Union[Image.Image, None] = None
        try:
            if f.suffix.lower() in supported_pdf_suffixes:
                print(f"Convertendo PDF: {file_name}...")
                images = cast(
                    List[Image.Image],
                    convert_from_path(file_path, first_page=1, last_page=1)
                )
                if not images:
                    results[file_name] = {"error": "ERROR: PDF vazio ou falha na conversão."}
                    continue
                temp_img = images[0]
            elif f.suffix.lower() not in supported_img_suffixes:
                continue
            input_data: Union[str, Image.Image] = temp_img if temp_img is not None else file_path
            raw_result: OCRResult = ocr(input_data)
            results[file_name] = raw_result
        except Exception as e:
            error_msg = f"ERROR: {type(e).__name__}: {e}"
            print(f"Erro ao processar o arquivo {file_name}: {error_msg}")
            results[file_name] = {"error": error_msg}
    return results


def main():
    results: Dict[str, OCRResult] = process_all()
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
