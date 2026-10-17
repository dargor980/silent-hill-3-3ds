# F00.02 / F00.03: inspección de ISO europea

Informe histórico de la etapa inicial. Estado posterior de la edición: [F00.02 completada por contraste con catálogo](f00-02-edition-identification.md). Las cifras y limitaciones de esta etapa se conservan como evidencia histórica.

Fecha: 2026-10-16. Responsable de ejecución: agente de desarrollo. Requisitos: RF01.01-RF01.04, RNF06.04, RNF07.06-RNF07.09, RNF08.01 y RNF11.05-RNF11.09. Repositorio con cambios locales aún sin commit; versión de inspector 1 y pycdlib 1.22.0.

Entrada: ISO local aportada por el usuario. Esperado: identificar arranque, catálogo, tamaños y SHA-256 sin extraer recursos; rechazar manifiestos incompatibles y datos malformados. Resultado: serial SLES-51434, PAL, VER de arranque 1.02; 113 archivos leídos y una segunda ejecución coincidente. [Comparación y hashes](../compatibility/edition-comparison.md).

## Reproducción

Con el entorno de desarrollo instalado desde `requirements-dev.lock` (o, solo para inspección, `requirements-tools.lock`), crear `reports/local` y ejecutar:

```sh
.venv/bin/python -m tools.pipeline.inspect_iso \
  --iso 'binaries/Silent Hill 3 (Europe) (En,Fr,De,Es,It).iso' \
  --region Europe --output reports/local/europe-disc.json
```

El destino debe ser nuevo. El informe guarda el perfil completo en su propiedad `profile`; se conserva esa propiedad como `reports/local/europe-profile.json`. Para verificarlo en otra lectura:

```sh
.venv/bin/python -m tools.pipeline.inspect_iso \
  --iso 'binaries/Silent Hill 3 (Europe) (En,Fr,De,Es,It).iso' \
  --region Europe --profile reports/local/europe-profile.json \
  --output reports/local/europe-disc-verified.json
```

Resultados: `observed` y `matched_local_profile`, respectivamente. Ambos mantienen `compatibility=unverified` y `extraction=not_performed`. La coincidencia con un manifiesto generado localmente prueba estabilidad/reidentificación de esta copia, no autenticidad respecto de un catálogo independiente ni soporte de extracción. Los dos informes y el perfil son locales e ignorados por Git.

Comprobación independiente con `shasum -a 256` sobre la ISO: coincide con `9a94b95e777dae426043e40df1b70d77c8f6960dbd79af10df1cd592cf99ad91`.

## Diseño y límites

- `disc.py`: reglas de arranque, cabecera ELF y perfil, sin filesystem ni dependencia de pycdlib; depende del puerto pequeño `DiscReader`.
- `iso9660.py`: adaptador de lectura ISO9660, SHA-256 en bloques de hasta 1 MiB, límites de archivos/rutas y comprobación de cambios del original.
- `inspect_iso.py`: composición, argumentos, verificación de perfil opcional y JSON; no sobrescribe un destino existente.
- `check_repository.py`: política de publicación separada de las reglas de identificación.

La sustitución del adaptador se prueba con una implementación en memoria y una ISO sintética que producen el mismo resultado. No se añade una interfaz de extracción a quien solo necesita leer/identificar. El adaptador admite nombres ISO9660 versión `;1`; rechaza archivos multiextent. No declara soporte de decodificación MFA/AFS, ni monta imágenes, ni ejecuta binarios PS2.

pycdlib procesa metadatos al abrir la imagen. Los límites propios de cantidad, rutas y extensiones se aplican después de ese parseo; no constituyen un límite de memoria o tiempo para cualquier imagen adversarial posible. Antes de ampliar a entradas públicas arbitrarias se requiere aislamiento y presupuesto del proceso. En esta tarea la entrada real es la copia local aportada y las pruebas adversariales son sintéticas.

## Pruebas

`tests/python/test_iso.py` genera discos pequeños con datos propios. Cubre contrato memoria/ISO, hashes completos, archivos faltantes, configuración inválida, ELF incorrecto, ISO truncada/ilegible, extents fuera de rango, versión de archivo no admitida, cambios durante lectura, symlinks, perfil parcial/incompatible, hash alterado, errores de salida y protección contra sobrescritura. Los tests de custodia comprueban ISO ignorada, ISO forzada al índice y reporte privado versionado.

La CI existente descubre estas pruebas mediante pytest e instala pycdlib desde el lock con hashes. Solo sube XML/JSON de cobertura y JUnit, junto con los artefactos sintéticos definidos en el workflow; el informe de la ISO no está entre ellos. La ejecución de GitHub Actions permanece pendiente de subir los cambios. No se modifica código C++ ni el diagnóstico 3DS en este incremento.

Resultado local final: **101/101 pruebas Python pasan**, Ruff y formato pasan; arquitectura/custodia/trazabilidad pasan. Cobertura de las herramientas propias: 437/460 líneas (95.00 %) y 173/186 ramas (93.01 %), superiores al umbral de 80 % por métrica. Python host 3.14.6; reportes en `build/pytest.xml` y `build/python-coverage.{json,xml}`.

Identidad del código probado: `build/iso-inspector-source-manifest.json`, SHA-256 `9b025d3dfbe5d49c3fde321c6a59a9d4014129577bedb95c9affc3da90011888`; contiene hashes de herramientas Python, tests y locks. No incluye el original. El estado aún no tiene commit.
