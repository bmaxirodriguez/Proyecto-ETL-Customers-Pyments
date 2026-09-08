"""
Orquestación del ETL: lectura, validación de esquema, calidad,
escritura atómica de salidas y generación de reportes.
"""

import os
import shutil
import json
import tempfile
from datetime import datetime, timezone

import pandas as pd

from etl_app.schema import (
    CUSTOMERS_REQUIRED_COLUMNS,
    PAYMENTS_REQUIRED_COLUMNS,
    SchemaError,
    validate_columns,
)
from etl_app.quality import process_customers, process_payments


def read_csv_safe(path, file_label):
    """Lee un CSV como strings. Si no existe o falla, es un error grave."""
    if not os.path.isfile(path):
        raise SchemaError(f"[{file_label}] Archivo no encontrado: {path}")
    return pd.read_csv(path, dtype=str, keep_default_na=True)


def write_json(path, data):
    """Escribe un dict como JSON legible."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def publish(tmp_dir, final_dir):
    """Mueve el directorio temporal al final, reemplazándolo. Es la operación atómica."""
    if os.path.exists(final_dir):
        shutil.rmtree(final_dir)
    os.replace(tmp_dir, final_dir)


def run_pipeline(customers_path, payments_path, run_date, output_dir, strict):
    """
    Ejecuta el ETL en 5 pasos:
      1. Leer y validar esquema
      2. Aplicar reglas de calidad
      3. Armar el quality_report y el manifest
      4. Escribir todo en una carpeta temporal
      5. Publicar de forma atómica (o abortar si algo salió mal)
    """
    final_dir = os.path.join(output_dir, f"run_date={run_date}")
    now = datetime.now(timezone.utc).isoformat()
    os.makedirs(output_dir, exist_ok=True)
    tmp_dir = tempfile.mkdtemp(prefix=".tmp_run_", dir=output_dir)

    # --- Paso 1 y 2: leer, validar esquema, aplicar calidad ---
    try:
        customers_raw = read_csv_safe(customers_path, "customers")
        payments_raw = read_csv_safe(payments_path, "payments")
        validate_columns(customers_raw, CUSTOMERS_REQUIRED_COLUMNS, "customers")
        validate_columns(payments_raw, PAYMENTS_REQUIRED_COLUMNS, "payments")

        acc_customers, rej_customers = process_customers(customers_raw)
        acc_payments, rej_payments = process_payments(
            payments_raw, valid_customer_ids=acc_customers["customer_id"].tolist()
        )
    except SchemaError as e:
        # Error grave: no hay datos que publicar. Solo dejamos el reporte de bloqueo.
        report = {"run_date": run_date, "generated_at": now, "status": "blocked", "blocked_reason": str(e)}
        write_json(os.path.join(tmp_dir, "quality_report.json"), report)
        write_json(os.path.join(tmp_dir, "manifest.json"),
                   {"run_date": run_date, "generated_at": now, "status": "blocked", "files": ["quality_report.json"]})
        publish(tmp_dir, final_dir)
        return {"status": "blocked", "quality_report": report, "output_dir": final_dir}

    # --- Paso 3: armar el reporte de calidad ---
    sum_valid = float(round(acc_payments["amount"].sum(), 2)) if len(acc_payments) else 0.0
    report = {
        "run_date": run_date,
        "generated_at": now,
        "customers": {"read": len(customers_raw), "accepted": len(acc_customers), "rejected": len(rej_customers)},
        "payments": {"read": len(payments_raw), "accepted": len(acc_payments), "rejected": len(rej_payments)},
        "sum_valid_payments": sum_valid,
        "status": "published",
    }

    # --- Paso 4: escribir todo en la carpeta temporal ---
    acc_customers.to_csv(os.path.join(tmp_dir, "customers.csv"), index=False)
    acc_payments.to_csv(os.path.join(tmp_dir, "payments.csv"), index=False)
    rej_customers.to_csv(os.path.join(tmp_dir, "rejected_customers.csv"), index=False)
    rej_payments.to_csv(os.path.join(tmp_dir, "rejected_payments.csv"), index=False)
    write_json(os.path.join(tmp_dir, "quality_report.json"), report)
    write_json(os.path.join(tmp_dir, "manifest.json"), {
        "run_date": run_date,
        "generated_at": now,
        "status": "published",
        "files": ["customers.csv", "payments.csv", "rejected_customers.csv",
                  "rejected_payments.csv", "quality_report.json"],
    })

    # --- Paso 5: publicar de forma atómica ---
    publish(tmp_dir, final_dir)
    return {"status": "published", "quality_report": report, "output_dir": final_dir}