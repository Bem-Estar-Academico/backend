from __future__ import annotations

import pytesseract
import os
import json
import logging
from PIL import Image
from typing import Union, Dict, Any, List
from dotenv import load_dotenv

from google import genai
from google.genai import types

load_dotenv()

TESSERACT_LANG: str = "por+eng"
TESSERACT_CONFIG: str = "--oem 3 --psm 3"
SCHEMA_RG: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "nome": {
            "type": "string",
            "description": "O nome completo extraído, em CAIXA ALTA.",
        },
        "cpf": {
            "type": "string",
            "description": "O CPF extraído, no formato 000.000.000-00.",
        },
        "rg": {
            "type": "string",
            "description": "O RG ou Personal Number do documento. Se for o novo RG (CIN), use o valor do CPF.",
        },
        "data_nascimento": {
            "type": "string",
            "description": "A data de nascimento extraída, no formato DD/MM/AAAA.",
        },
    },
    "required": ["nome", "cpf", "rg", "data_nascimento"],
}

SCHEMA_CNH: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "nome": {
            "type": "string",
            "description": "O nome completo extraído, em CAIXA ALTA.",
        },
        "cpf": {
            "type": "string",
            "description": "O CPF extraído, no formato 000.000.000-00.",
        },
        "rg_numero": {
            "type": "string",
            "description": "O número do RG (ou o número de identidade usado na emissão da CNH).",
        },
        "data_nascimento": {
            "type": "string",
            "description": "A data de nascimento extraída, no formato DD/MM/AAAA.",
        },
    },
    "required": ["nome", "cpf", "rg_numero", "data_nascimento"],
}

FALLBACK_DESCRIPTIONS: Dict[str, str] = {
    "nome": "O nome completo da pessoa, em CAIXA ALTA.",
    "cpf": "O CPF da pessoa, no formato 000.000.000-00.",
    "rg": "O RG ou Personal Number do documento. Pode ser igual ao CPF.",
    "data_nascimento": "A data de nascimento da pessoa, no formato DD/MM/AAAA.",
    "rg_numero": "O número do RG ou da identidade usado na CNH.",
}

PROMPT_RG = (
    "Você é um extrator de dados de documentos (RG/CIN). Analise o texto OCR bruto abaixo "
    "e extraia APENAS os seguintes campos: 'Nome Completo', 'CPF', 'RG', 'Data de Nascimento', 'Sexo' e 'Nacionalidade'. "
    "O Nome Completo deve ser formatado em CAIXA ALTA. Todas as datas devem estar no formato DD/MM/AAAA. "
    "O campo 'RG' deve ser preenchido com o 'Registro Geral' ou o 'Personal Number'. Se for o novo RG (CIN), use o valor do CPF. "
    "Se o dado não for encontrado, use o valor 'null'. Sua resposta DEVE ser um objeto JSON estritamente conforme o schema fornecido.\n\n"
    "Texto OCR: {}"
)

PROMPT_CNH = (
    "Você é um extrator de dados de Carteira Nacional de Habilitação (CNH). Analise o texto OCR bruto "
    "e extraia APENAS os seguintes campos: 'Nome Completo', 'CPF', 'RG', e 'Data de Nascimento'. "
    "O Nome Completo deve ser formatado em CAIXA ALTA. Todas as datas devem estar no formato DD/MM/AAAA. "
    "Se o dado não for encontrado, use o valor 'null'. Sua resposta DEVE ser um objeto JSON estritamente conforme o schema fornecido.\n\n"
    "Texto OCR: {}"
)


def extract_single_field_fallback(
    raw_text: str, field_key: str, field_description: str, model: str = "gemini-2.5-pro"
) -> Union[str, None]:
    try:
        client = genai.Client()
        fallback_schema: Dict[str, Any] = {
            "type": "object",
            "properties": {
                field_key: {"type": "string", "description": field_description},
            },
            "required": [field_key],
        }

        fallback_prompt = (
            f"Você é um extrator de dados focado. Analise o texto OCR bruto abaixo e extraia APENAS o '{field_key}'. "
            f"{field_description}. Se o dado não for encontrado, use o valor 'null'. "
            f"Sua resposta DEVE ser um objeto JSON com a chave '{field_key}'.\n\n"
            f"Texto OCR: {raw_text}"
        )
        config = types.GenerateContentConfig(
            response_mime_type="application/json", response_schema=fallback_schema
        )
        response = client.models.generate_content(
            model=model,
            contents=[fallback_prompt],
            config=config,
        )
        if response.text:
            data = json.loads(response.text)
            return data.get(field_key)
    except Exception:
        pass
    return None


def identify_document_type(raw_text: str) -> str:
    text_upper = raw_text.upper()
    text_upper = (
        text_upper.replace("Ç", "C")
        .replace("Ã", "A")
        .replace("É", "E")
        .replace("Ê", "E")
        .replace("Õ", "O")
        .replace("Í", "I")
        .replace("Ú", "U")
    )
    if any(
        term in text_upper
        for term in ["HABILITAC", "DRIVER", "CNH", "CONDUCAO", "PERMISSAO"]
    ):
        return "CNH"
    elif any(
        term in text_upper
        for term in ["IDENTIDADE", "REGISTRO GERAL", "PERSONAL NUMBER", "IDENTIFICACAO"]
    ):
        return "RG"
    return "UNKNOWN"


def extract_fields_with_llm(raw_text: str) -> Dict[str, Union[str, Dict[str, Any]]]:
    if not os.getenv("GEMINI_API_KEY"):
        return {"error": "GEMINI_API_KEY not found. Cannot use LLM."}
    doc_type = identify_document_type(raw_text)

    if doc_type == "CNH":
        response_schema = SCHEMA_CNH
        prompt = PROMPT_CNH.format(raw_text)
    elif doc_type == "RG":
        response_schema = SCHEMA_RG
        prompt = PROMPT_RG.format(raw_text)
    else:
        return {"error": "Document type could not be identified."}

    try:
        client = genai.Client()
        config = types.GenerateContentConfig(
            response_mime_type="application/json", response_schema=response_schema
        )
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[prompt],
            config=config,
        )
        if response.text is None:
            return {"error": "LLM returned empty response on main pass"}
        data = json.loads(response.text)
        required_fields: List[str] = response_schema.get("required", [])
        for field_key in required_fields:
            if data.get(field_key) in [None, "null"]:
                field_description = FALLBACK_DESCRIPTIONS.get(
                    field_key,
                    f"Extraia o campo '{field_key}'. Formate-o de forma limpa.",
                )
                logging.warning(
                    f"Campo '{field_key}' falhou. Tentando Fallback Focado..."
                )
                fallback_value = extract_single_field_fallback(
                    raw_text, field_key, field_description
                )
                if fallback_value not in [None, "null"]:
                    data[field_key] = fallback_value
                    logging.warning(f"Fallback SUCCEEDED para {field_key}.")
                else:
                    logging.warning(f"Fallback FAILED para {field_key}.")

        return {"extracted_fields": data}

    except Exception as e:
        return {"error": f"LLM Extraction failed: {e}"}


def ocr(path_or_pil: Union[str, Image.Image]) -> Dict[str, Union[str, Dict[str, Any]]]:
    pil: Image.Image
    if isinstance(path_or_pil, str):
        pil = Image.open(path_or_pil)
    else:
        pil = path_or_pil
    full_text: str = str(
        pytesseract.image_to_string(  # type: ignore
            pil, lang=TESSERACT_LANG, config=TESSERACT_CONFIG
        )
    ).strip()

    extracted_result = extract_fields_with_llm(full_text)
    return extracted_result
