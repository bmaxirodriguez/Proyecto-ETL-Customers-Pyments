"""Interfaz de línea de comandos del ETL."""

import argparse
import os
import sys
from datetime import datetime

from etl_app.pipeline import run_pipeline


def build_parser():
    """Arma el parser de argumentos. Solo existe el subcomando 'run'."""
    parser = argparse.ArgumentParser(prog="python -m etl_app")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Ejecuta el ETL.")
    run_parser.add_argument("--customers", required=True)
    run_parser.add_argument("--payments", required=True)
    run_parser.add_argument("--run-date", required=True)
    run_parser.add_argument("--output-dir", required=True)
    run_parser.add_argument("--strict", action="store_true")

    return parser


def validate_inputs(args):
    """Chequeos previos a correr el pipeline: fecha válida y archivos existentes."""
    try:
        datetime.strptime(args.run_date, "%Y-%m-%d")
    except ValueError:
        sys.exit(f"Error: --run-date debe ser YYYY-MM-DD (recibido: '{args.run_date}')")

    if not os.path.isfile(args.customers):
        sys.exit(f"Error: no se encontró el archivo --customers: {args.customers}")

    if not os.path.isfile(args.payments):
        sys.exit(f"Error: no se encontró el archivo --payments: {args.payments}")


def print_summary(result, strict):
    """Imprime en consola el resultado de la corrida."""
    report = result["quality_report"]
    print(f"Estado: {result['status']}")
    print(f"Salida: {result['output_dir']}")

    if result["status"] == "blocked":
        print(f"Motivo de bloqueo: {report.get('blocked_reason')}")
        return 1 if strict else 0

    print(f"Customers -> leidos: {report['customers']['read']}, "
          f"aceptados: {report['customers']['accepted']}, "
          f"rechazados: {report['customers']['rejected']}")
    print(f"Payments  -> leidos: {report['payments']['read']}, "
          f"aceptados: {report['payments']['accepted']}, "
          f"rechazados: {report['payments']['rejected']}")
    print(f"Suma de pagos validos: {report['sum_valid_payments']}")
    return 0


def main(argv=None):
    args = build_parser().parse_args(argv)
    validate_inputs(args)

    result = run_pipeline(
        customers_path=args.customers,
        payments_path=args.payments,
        run_date=args.run_date,
        output_dir=args.output_dir,
        strict=args.strict,
    )

    exit_code = print_summary(result, args.strict)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()