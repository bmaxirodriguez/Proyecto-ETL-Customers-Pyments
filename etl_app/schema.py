
CUSTOMERS_REQUIRED_COLUMNS = ["customer_id", "name", "status"]
PAYMENTS_REQUIRED_COLUMNS = ["payment_id", "customer_id", "amount", "paid_at"]

VALID_STATUSES = {"active", "inactive"}


class SchemaError(Exception):
    
    pass


def validate_columns(df, required_columns, file_label):
    
    missing = [col for col in required_columns if col not in df.columns]
    if missing:
        raise SchemaError(
            f"[{file_label}] Faltan columnas requeridas: {missing}. "
            f"Columnas encontradas: {list(df.columns)}"
        )