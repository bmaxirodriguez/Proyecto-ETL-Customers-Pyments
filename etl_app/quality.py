"""
Reglas de calidad de datos: detección de filas inválidas.

"""

import pandas as pd
from etl_app.normalize import parse_amount, normalize_status


def process_customers(df):
    """
    Aplica reglas de calidad sobre customers.
    Devuelve (accepted_df, rejected_df).
    Reglas:
      - customer_id nulo -> rechazado
      - customer_id duplicado -> se acepta la 1ra aparición, se rechazan las siguientes
    """
    df = df.copy()
    df["error_reason"] = None

    # Normalizar status
    df["status"] = df["status"].apply(normalize_status)

    # Regla 1: customer_id nulo o vacío
    is_null_id = df["customer_id"].isna() | (df["customer_id"].astype(str).str.strip() == "")
    df.loc[is_null_id, "error_reason"] = "missing_customer_id"

    # Regla 2: customer_id duplicado (se queda la 1ra, se rechazan las repetidas siguientes)
    is_duplicate = df["customer_id"].duplicated(keep="first") & ~is_null_id
    df.loc[is_duplicate, "error_reason"] = "duplicate_customer_id"

    rejected = df[df["error_reason"].notna()].copy()
    accepted = df[df["error_reason"].isna()].drop(columns=["error_reason"]).copy()

    return accepted, rejected


def process_payments(df, valid_customer_ids):
    """
    Aplica reglas de calidad sobre payments.
    Devuelve (accepted_df, rejected_df).
    Reglas:
      - payment_id nulo -> rechazado
      - payment_id duplicado -> se acepta la 1ra, se rechazan las siguientes
      - customer_id no existe en customers válidos -> rechazado
      - amount no convertible -> rechazado (invalid_amount_format)
      - amount convertible pero <= 0 -> rechazado (amount_not_positive)
    """
    df = df.copy()
    df["error_reason"] = None

    # Normalizar amount antes de validar (para poder chequear positividad)
    df["amount"] = df["amount"].apply(parse_amount)

    # Regla 1: payment_id nulo/vacío
    is_null_pid = df["payment_id"].isna() | (df["payment_id"].astype(str).str.strip() == "")
    df.loc[is_null_pid, "error_reason"] = "missing_payment_id"

    # Regla 2: payment_id duplicado
    is_duplicate = df["payment_id"].duplicated(keep="first") & ~is_null_pid
    df.loc[is_duplicate & df["error_reason"].isna(), "error_reason"] = "duplicate_payment_id"

    # Regla 3: customer_id no existe en customers válidos
    no_customer = ~df["customer_id"].isin(valid_customer_ids)
    df.loc[no_customer & df["error_reason"].isna(), "error_reason"] = "customer_not_found"

    # Regla 4: amount no convertible (quedó None tras parse_amount)
    invalid_format = df["amount"].isna()
    df.loc[invalid_format & df["error_reason"].isna(), "error_reason"] = "invalid_amount_format"

    # Regla 5: amount convertible pero <= 0
    not_positive = df["amount"].notna() & (df["amount"] <= 0)
    df.loc[not_positive & df["error_reason"].isna(), "error_reason"] = "amount_not_positive"

    rejected = df[df["error_reason"].notna()].copy()
    accepted = df[df["error_reason"].isna()].drop(columns=["error_reason"]).copy()

    return accepted, rejected
