
import re


def parse_amount(raw):
    """
    Convierte un string de monto a float, soportando varios formatos:
      - "1.234,56"  -> formato europeo (punto=miles, coma=decimal) -> 1234.56
      - "$ 200"     -> símbolo de moneda -> 200.0
      - "50.00"     -> formato US, ya estándar -> 50.0
      - "abc"       -> no convertible -> None

    Devuelve:
        float si se pudo convertir, None si el valor es inválido.
    """
    if raw is None:
        return None

    text = str(raw).strip()
    if text == "":
        return None

    # Quitar símbolos de moneda y espacios (ej: "$ 200" -> "200")
    text = re.sub(r"[^\d,.\-]", "", text)

    if text == "" or text == "-":
        return None

    has_comma = "," in text
    has_dot = "." in text

    try:
        if has_comma and has_dot:
            # Formato europeo: "1.234,56" -> punto=miles, coma=decimal
            text = text.replace(".", "").replace(",", ".")
        elif has_comma and not has_dot:
            # Solo coma: "200,50" -> coma es decimal
            text = text.replace(",", ".")
        # Si solo hay punto (o ninguno), ya está en formato válido para float()

        value = float(text)
        return value
    except ValueError:
        return None


def normalize_status(raw):
    """Normaliza el campo status: minúsculas y sin espacios extra."""
    if raw is None:
        return None
    return str(raw).strip().lower()