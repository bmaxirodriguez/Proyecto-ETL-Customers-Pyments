"""
Tests automáticos del ETL.

Cada test es autocontenido: arma sus propios datos de ejemplo
(no depende de los CSV reales en input/), así corre igual en cualquier PC.
"""

import pandas as pd

from etl_app.normalize import parse_amount
from etl_app.quality import process_customers, process_payments
from etl_app.pipeline import run_pipeline


# ---------------------------------------------------------------------
# Test 1: la funcion parse_amount convierte bien los 3 formatos del enunciado (R3)
# ---------------------------------------------------------------------
def test_parse_amount_formatos_variados():
    assert parse_amount("1.234,56") == 1234.56   # formato europeo (punto=miles, coma=decimal)
    assert parse_amount("$ 200") == 200.0         # simbolo de moneda
    assert parse_amount("50.00") == 50.0          # formato ya estandar
    assert parse_amount("abc") is None            # no numerico -> None, no explota


# ---------------------------------------------------------------------
# Test 2: un customer_id repetido se rechaza, solo se acepta la 1ra vez (R4)
# ---------------------------------------------------------------------
def test_customer_id_duplicado_se_rechaza():
    df = pd.DataFrame({
        "customer_id": ["C001", "C002", "C002"],
        "name": ["Ana", "Luis", "Luis"],
        "status": ["active", "active", "active"],
    })

    accepted, rejected = process_customers(df)

    assert len(accepted) == 2      # C001 y la 1ra aparicion de C002
    assert len(rejected) == 1      # la 2da aparicion de C002
    assert rejected.iloc[0]["error_reason"] == "duplicate_customer_id"


# ---------------------------------------------------------------------
# Test 3: un pago que referencia un cliente que no existe se rechaza (R4)
# ---------------------------------------------------------------------
def test_pago_sin_cliente_valido_se_rechaza():
    payments = pd.DataFrame({
        "payment_id": ["P1", "P2"],
        "customer_id": ["C001", "C999"],
        "amount": ["100.00", "50.00"],
        "paid_at": ["2026-08-24", "2026-08-24"],
    })

    accepted, rejected = process_payments(payments, valid_customer_ids=["C001"])

    assert len(accepted) == 1
    assert len(rejected) == 1
    assert rejected.iloc[0]["error_reason"] == "customer_not_found"


# ---------------------------------------------------------------------
# Test 4: un monto negativo o cero se rechaza, aunque sea un numero valido (R4)
# ---------------------------------------------------------------------
def test_monto_no_positivo_se_rechaza():
    payments = pd.DataFrame({
        "payment_id": ["P1"],
        "customer_id": ["C001"],
        "amount": ["-5.00"],
        "paid_at": ["2026-08-24"],
    })

    accepted, rejected = process_payments(payments, valid_customer_ids=["C001"])

    assert len(accepted) == 0
    assert len(rejected) == 1
    assert rejected.iloc[0]["error_reason"] == "amount_not_positive"


# ---------------------------------------------------------------------
# Test 5: correr el pipeline completo dos veces da el mismo resultado (R6, idempotencia)
# ---------------------------------------------------------------------
def test_pipeline_es_idempotente(tmp_path):
    customers_csv = tmp_path / "customers.csv"
    payments_csv = tmp_path / "payments.csv"

    customers_csv.write_text(
        "customer_id,name,status\nC001,Ana,active\nC002,Luis,active\n"
    )
    payments_csv.write_text(
        "payment_id,customer_id,amount,paid_at\n"
        "P1,C001,100.00,2026-08-24\n"
        "P2,C002,50.00,2026-08-24\n"
    )

    resultado_1 = run_pipeline(
        customers_path=str(customers_csv),
        payments_path=str(payments_csv),
        run_date="2026-08-24",
        output_dir=str(tmp_path / "output"),
        strict=True,
    )
    resultado_2 = run_pipeline(
        customers_path=str(customers_csv),
        payments_path=str(payments_csv),
        run_date="2026-08-24",
        output_dir=str(tmp_path / "output"),
        strict=True,
    )

    assert resultado_1["quality_report"]["customers"] == resultado_2["quality_report"]["customers"]
    assert resultado_1["quality_report"]["payments"] == resultado_2["quality_report"]["payments"]
    assert resultado_1["quality_report"]["sum_valid_payments"] == resultado_2["quality_report"]["sum_valid_payments"]