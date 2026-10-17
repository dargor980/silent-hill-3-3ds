# F02.02 — evaluación del candidato MFA y alternativa de inspección

Fecha: **2026-10-17** (America/Santiago). **Completada como evaluación y selección de alternativa**, conforme a la opción de alternativa documentada del ticket. No hay extractor acreditado ni cierre G02. [Ticket detallado](../specs/sh3-3ds/tasks/F02.md#f0202), [contrato EARS M01-M08](../../schemas/mfa-probe-v1.md) y [procedencia fijada](../compatibility/mfa-candidate-evidence.json).

## Decisión del candidato

Se fijó MFA Tool de RayneDuarte en el commit **`6c362d2c163236c0496c42ed297eb9c07487ab69`**, fechado 2025-12-06T16:41:18Z. La rama por defecto observada ahora es `main`; la mención `master` del inventario inicial no es un pin válido. Se consultaron cinco fuentes/documentos, con URL, tamaño y SHA-256 conservados en el JSON de procedencia. No se descargó ni ejecutó el `.exe`, no se compiló el candidato y no se copió su código al proyecto.

El proyecto declara C++Builder/VCL y Win32/Win64; el host usado es Darwin arm64. La revisión estática confirma una GUI Windows, sin CLI portable observada en los archivos examinados. No se probó Wine ni una VM; no se afirma incompatibilidad bajo todos los entornos posibles. El candidato no se selecciona para la automatización actual.

Su lector sustituye determinados caracteres de los nombres y crea salidas desde el directorio de trabajo. La revisión no encontró validación explícita de confinamiento/rangos comparable al contrato del proyecto. No se presume pérdida o explotación real: no se ejecutó. Esas propiedades son razones para preferir un sondeo propio y conservar nombres sin transformaciones silenciosas.

La API devuelve licencia nula y el árbol consultado no contiene una licencia global identificada. LIC04 permanece abierto para adoptar/copiar ese código. Se consultó también el [script público del autor bajo el nombre Silent Hill 3](https://aluigi.altervista.org/bms/silent_hill_3.bms): 252 bytes, SHA-256 `8119db39a1eea7895e0182f76190ef650192c5e2b081f20bdc1d9e226803395f`. Su tabla describe otra disposición; no confirma el antecedente MFA exacto mencionado por el candidato. No se ejecuta ni adopta ese script.

Se elige **implementación propia de inspección D8**, con referencia de campos atribuida al [lector fijado del candidato](https://github.com/RayneDuarte/MFA-Tool-for-Silent-Hill-3-PS2-/blob/6c362d2c163236c0496c42ed297eb9c07487ab69/mfa_reader.cpp), política conservadora propia y comprobación sobre bytes reales. Al haberse leído código externo, no se presenta como clean room. El pin/lectura de fuentes no demuestra equivalencia funcional ni autoriza redistribuir el candidato.

## Resultado sobre la edición europea

En cada una de dos ejecuciones se verificó el SHA-256 de la imagen completa y todos los tamaños/hashes del perfil de 113 archivos antes del sondeo. Imagen de 3.586.785.280 bytes, SHA-256 `9a94b95e777dae426043e40df1b70d77c8f6960dbd79af10df1cd592cf99ad91`; perfil canónico `ps2-sles-51434-9a94b95e777dae42`, SLES-51434/PAL 1.02. El perfil mantiene SHA-256 `504cb4aa3a0a24480324d2853a153ff9c77ac7b8987b3665566b8ed8f9a620d9`, sin capacidades de extracción.

| Unidad | Resultado | Alcance |
|---|---|---|
| B0.MFA | `structural_candidate`, 1 bloque, 40 entradas | Tabla inicial D8, nombres/rangos y final exacto comprobados |
| MV0.MFA | `structural_candidate`, 1 bloque, 7 entradas | Misma política; bytes de películas no decodificados |
| 59 archivos de X0-X3 | `unknown`, `MFA_TABLE` | Cabeceras iniciales apuntan a variante B8; no se prueba esa variante como fallback |
| XBG0.MFA | `unknown`, `MFA_NAME` | La cadena D8 encuentra un nombre fuera de la política ASCII; no se acepta un subconjunto de sus bloques |

Total: **62 candidatos por extensión, 2 candidatos estructurales, 60 desconocidos**; **47 entradas** y **2 bloques aceptados estructuralmente**. Esto no es 2/62 de cobertura de contenido jugable ni certificación del formato completo. Los nombres `.mfa` seleccionan entradas para investigación; la aceptación depende de los checks de estructura.

Un diagnóstico adicional de solo lectura situó el rechazo XBG0 en el nombre de la entrada ordinal 237: offset relativo 936, tabla termina en 784, NUL en 969 y ocho bytes fuera de ASCII imprimible. No se guardó ni imprimió el nombre crudo. Esto justifica investigar codificación en F02.03; **no demuestra corrupción** ni identifica automáticamente UTF-8, Shift-JIS u otra codificación. No se relajó el parser para aceptar esta muestra.

Los dos informes privados, ignorados por Git, son idénticos byte por byte:

- `reports/local/f02-02-mfa-probe.json`.
- `reports/local/f02-02-mfa-probe-repeat.json`.

Cada uno mide **21.492 bytes** y tiene SHA-256 **`fd1cbe93a1e49b175a2fcfd60efa54ee32b8d086d89342514cc92b4dddc5e32b`**. Solo contienen metadatos, sin payloads, tablas crudas, nombres internos ni rutas del host. La ISO se abrió en lectura y su estabilidad se comprobó al cerrar. El hash completo sí lee todos sus bytes para identidad; el parser lee únicamente sectores de metadatos. No se creó una raíz de extracción porque no se exportaron recursos.

## Implementación, pruebas y pipeline

`mfa.inspect_d8` valida una cadena completa usando un puerto mínimo; `MemberRange` adapta un miembro ISO; `IsoImage.read_range` confina rangos y entrega lecturas exactas de hasta 4096 bytes; `mfa_probe` reutiliza inventario/perfil y escribe tras cierre estable. Las responsabilidades de formato, I/O y composición permanecen separadas. No cambian dependencias, SDK ni runtime.

El parser limita bloques/entradas, tamaño de tabla y cadenas; exige límites del contenedor, nombres relativos, ausencia de colisiones y de solapamientos de datos. Distingue error de formato (`unknown` por archivo) de fallo de transporte/identidad (aborta toda la operación). No usa heurística para elegir B8 ni adivina semántica de la palabra desconocida, que en los dos bloques aceptados vale 33204.

**430/430 pruebas Python aprobadas**, incluidas **73 nuevas** para M01-M08. Los 177 casos focalizados ISO/inventario/MFA pasaron antes del contraste real. La batería cubre:

- Uno/múltiples bloques, entrada vacía, espacios conservados y payload virtual de 1 GiB sin asignarlo ni leerlo.
- Tablas/nombres truncados, tamaño y conteos extremos, terminación/ASCII, límite de nombre, presupuestos, rutas absolutas/traversal, duplicados y conflictos archivo/directorio entre bloques, rangos y solapamientos.
- Variantes B8/desconocidas sin falso éxito; fallo de lectura distinto de error de formato; sustitución memoria/ISO con mismo resultado.
- Perfil/hash alterado, cambio de imagen al cerrar, destino existente/enlace/directorio ausente y dos salidas idénticas sin payload ni ruta local.

Cobertura: **973/1003 líneas (97,01 %)** y **375/392 ramas (95,66 %)**. `mfa.py` alcanza 100 % de líneas/ramas. Gate independiente ≥80 %, Ruff check/format y contratos de arquitectura/custodia/specs se conservan en `build/f02-02/quality.log` y `verification.json`.

La primera ejecución focalizada tuvo dos fallos en el doble de lectura: pycdlib no permite sustituir ese método en una instancia. Se corrigió la inyección en la clase, sin cambiar ni debilitar el comportamiento del lector, y se repitieron satisfactoriamente los casos.

Python 3.14.6, pytest 9.1.1, pycdlib 1.22.0 y Ruff 0.17.1. El job quality existente descubre las pruebas y cobertura; CI solo usa datos propios, sin red ni ISO original. No se ejecutó GitHub Actions remotamente ni se repitieron builds C++/ARM, porque ese código no cambió. G01 conserva sus pruebas físicas pendientes.

## Reproducción y continuación

Desde la raíz del proyecto, cada ejecución exige un destino nuevo:

```sh
rtk proxy .venv/bin/python -m tools.inspectors.mfa_probe \
  --iso 'binaries/Silent Hill 3 (Europe) (En,Fr,De,Es,It).iso' \
  --profile reports/local/europe-profile-identified.json \
  --image-sha256 9a94b95e777dae426043e40df1b70d77c8f6960dbd79af10df1cd592cf99ad91 \
  --output reports/local/f02-02-mfa-probe.json
```

La repetición cambia únicamente el destino por `f02-02-mfa-probe-repeat.json`. Comandos, logs de pytest, XML, cobertura y manifiesto de fuentes se conservan bajo `build/f02-02`; los cambios aún no están en un commit. Las fuentes externas consultadas permanecen fuera del repositorio, y sus identificadores/hashes se conservan como metadatos de procedencia.

**F02.02 se cierra como evaluación**, con rechazo de adopción del candidato GUI y alternativa de sondeo contrastada. La extracción efectiva, los hashes por recurso y las dependencias siguen pendientes. **F02.03** investigará B8 y el caso de nombres XBG0 en instancias separadas; F02.04 hará el catálogo interno, y F02.05 comparará dos extracciones en raíces privadas externas explícitas. Q05/G02 permanecen abiertos y LIC04 continúa aplicándose si se decide adoptar código del candidato.

## Identidad de fuentes

`build/f02-02/source-manifest.json`: 52 archivos; SHA-256 `52e5639272ada16d7d10d8abbdb4cf855b2ba2071a2c9c3fdde5ec176e57c5f6`. Excluye este informe para evitar autorreferencia, fuentes externas crudas y datos privados. Registra código Python, tests, contratos/documentación y configuración relevante; no sustituye un commit ni afirma reproducibilidad de un build C++ no ejecutado.
