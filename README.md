# Proyecto ETL Batch — Customers & Payments

Objetivo: Desarrollo de un proceso ETL por lotes que lee dos archivos .csv (`customers` y `payments`), valida su esquema, aplica reglas de calidad de datos, y publica archivos de salida de forma atómica e idempotente.

## Requisitos
- Python 3.10+


## Instalación

Desde la raíz del proyecto:

```bash
python -m venv venv

# Activar el entorno virtual
# Windows PowerShell:
.\venv\Scripts\Activate.ps1


# Instalar dependencias
pip install -r requirements.txt
```

## Estructura del proyecto
proyecto_colektia/
├── input/ #Archivos .csv de entrada (customers.csv, payments.csv)
├── etl_app/
│ ├── cli.py
│ ├── pipeline.py
│ ├── schema.py
│ ├── normalize.py
│ └── quality.py
├── tests/
│ └── test_etl.py
├── output/
├── README.md
└── DECISIONS.md

## Script para ejecutar

```bash
python -m etl_app run \
  --customers ./input/customers.csv \
  --payments ./input/payments.csv \
  --run-date 2026-08-24 \
  --output-dir ./output \
  --strict
```

### Argumentos

| Argumento | Descripción |
|---|---|
| `--customers` | Path del archivo .csv de clientes (requiere de columnas `customer_id,name,status`) |
| `--payments` | Path del archivo .csv de pagos (requiere de columnas `payment_id,customer_id,amount,paid_at`) |
| `--run-date` | Fecha de la corrida, formato `YYYY-MM-DD` |
| `--output-dir` | Carpeta donde se publican los resultados |
| `--strict` | Si hay un error grave de esquema, el programa genera el reporte pero no publica los datos finales |

## Salida generada
output/run_date=2026-08-24/
├── customers.csv
├── payments.csv
├── rejected_customers.csv
├── rejected_payments.csv
├── quality_report.json
└── manifest.json

## Reglas de calidad aplicadas

**Tabla Customers:**
- `customer_id` nulo/vacío -> rechazado (`missing_customer_id`)
- `customer_id` duplicado -> se acepta la 1ra aparición, se rechazan las siguientes (`duplicate_customer_id`)

**Tabla Payments:**
- `payment_id` nulo/vacío -> rechazado (`missing_payment_id`)
- `payment_id` duplicado -> se acepta la 1ra aparición, se rechazan las siguientes (`duplicate_payment_id`)
- `customer_id` que no existe entre los clientes válidos -> rechazado (`customer_not_found`)
- `amount` no convertible a número -> rechazado (`invalid_amount_format`)
- `amount` convertible pero <= 0 -> rechazado (`amount_not_positive`)

## Idempotencia y atomicidad

- Cada corrida se publica en `output/run_date=<fecha>/`. Correr el mismo comando dos veces sobrescribe esa carpeta por completo, sin duplicar ni acumular datos.
- La escritura se hace primero en una carpeta temporal; solo si todo terminó bien se reemplaza la carpeta final con un `os.replace`. Si algo falla a mitad de camino, la carpeta final nunca queda a medias.

## Tests

```bash
python -m pytest tests/ -v
```

Cubren: normalización de montos (3 formatos), duplicados de `customer_id`,
pagos con cliente inexistente, montos negativos, e idempotencia del pipeline completo.