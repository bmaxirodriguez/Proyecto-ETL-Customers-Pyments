# Decisiones de diseño.

## 1. Duplicados de customer_id y payment_id

**Decisión:** se acepta la primera aparición y se rechazan las siguientes, con `error_reason = 'duplicate_customer_id' o 'duplicate_payment_id'`.

**¿Por qué?:** un ID que se repite podría indicar una carga duplicada del mismo dato (por ejemplo: el mismo archivo procesado dos veces). Quedarse con la primera aparición es una regla simple y fácil de auditar. La alternativa podría ser rechazar ambas apariciones, que también sería válida, pero perderíamos información, es decir que si el registro es legítimo y solo se cargó dos veces por error, tiene sentido conservar una copia en vez de ninguna.

## 2. Normalización de montos (parse_amount)

**Decisión:** se distinguen 3 casos según el formato de orígen:
- Coma y punto juntos (`1.234,56`) -> formato europeo: el punto es separador de miles (se elimina) y la coma es el separador decimal (se convierte en punto).
- Solo coma (`200,50`) -> la coma se interpreta como separador decimal y se convierte en punto.
- Solo punto (`50.00`) -> ya está en un formato válido para Python.

Antes de aplicar esta lógica, se procedió a eliminar símbolos no numéricos (como `$` o espacios).

**¿Por qué?:** El obetivo es que el usuario no tenga que ingresar o indicar un formato particular. La estrategia usada (mirar qué separadores aparecen y en qué combinación) es una forma estándar de resolver esta ambigüedad sin conocer el origen del dato.

**Limitación:** un valor como `"1.234"` (sin coma) es ambiguo -- podría ser "mil doscientos treinta y cuatro" (miles, formato europeo) o "uno coma 234" (decimal, formato US). Con la regla actual se interpretaría como `1.234` (formato US, punto = decimal), porque no hay coma que indique el patrón europeo. Esto no afecta al dataset de este proyecto ya que no se presentó el caso, pero se documenta como supuesto explícito.

**Aclaración sobre amount = 0:** la regla actual rechaza tanto negativos como cero bajo el mismo motivo (amount_not_positive), asumiendo que un "payment" representa una transferencia real de dinero y que un monto de $0 no cumple esa definición. Esto sería una decisión de negocio en conjunto con el equipo, y no unicamente técnica: si el sistema de origen SÍ considera válidos los pagos de $0 (por ejemplo, facturas pagadas con descuento total), habría que separar esta regla en dos motivos distintos (amount_negative y amount_zero) para no perder esos casos como datos rechazados por error.

## 3. Consideración de "error grave" (bloquea publicación en --strict)

**Decisión:** Para este caso, solo la falta de columnas requeridas en el esquema (`SchemaError`) se considera un error grave que bloquea la publicación de `customers.csv` y `payments.csv`. Los problemas de fila (ID nulo, monto inválido, cliente inexistente, etc.) NO bloquean la publicación: esas filas se apartan a los archivos `rejected_*.csv` con su motivo, pero el resto de los datos válidos se publica.

**¿Por qué?:** un archivo con columnas faltantes es un problema estructural que afecta a todo el archivo, mientras que un problema en una fila individual es un inconveniente puntual que no debería impedir procesar el resto de las filas que están correctas. Esto respeta el criterio de aceptación: "datos malos no se publican como buenos, pero tampoco se pierden".

## 4. Atomicidad de la publicación

**Decisión:** Se escribe primero en una carpeta temporal (creada con `tempfile.mkdtemp` dentro del mismo `output_dir`), y solo al final se reemplaza la carpeta final con `os.replace(tmp_dir, final_dir)`

**¿Por qué?:** `os.replace` es una operación atómica a nivel de sistema de archivos (siempre que ambas carpetas estén en el mismo disco, por eso el directorio temporal se crea *dentro* de `output_dir` y no en otro lado). Si el proceso se interrumpe antes de esa línea, la carpeta final original queda
intacta; si se interrumpe después, la carpeta final ya es la nueva versión completa.

## 5. Idempotencia mediante particionado por run_date

**Decisión:** cada corrida se publica en `output/run_date=<fecha>/`, y esa carpeta se sobrescribe por completo en cada ejecución (no se le agregan archivos, se reemplaza entera).

**¿Por qué?:** al particionar por fecha y reemplazar la partición completa en cada corrida, ejecutar el mismo comando N veces con la misma entrada, da siempre el mismo resultado exacto (mismos conteos, mismos archivos).

## 6. Separación entre normalización y validación de negocio

**Decisión:** `parse_amount` (en `normalize.py`) solo se encarga de convertir un string a número o devolver `None` si es que no se puede convertir. No decide si el número es "válido para el negocio" (por ejemplo, si es positivo). Esa decisión vive en `quality.py`, como una regla aparte (`amount_not_positive`).

**¿Por qué?:** mantiene cada función con una sola responsabilidad. Además facilita testear la conversión de formato por separado de las reglas de negocio, y permite, de ser necesario, cambiar una regla de negocio (por ejemplo los montos también pueden ser negativos) sin tocar la lógica de parseo.