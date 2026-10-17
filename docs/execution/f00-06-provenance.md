# F00.06: revisión inicial de procedencia y licencias

Estado: **completada para el inventario inicial**. Fecha: 2026-10-16. Unidad: dependencias actuales y candidatos del PDF. Responsable de ejecución: agente de desarrollo. Requisitos RNF05.01/RNF08.03; revisión documental V19/V22, sin aprobación de distribución.

## Resultado

La [matriz de procedencia](../compatibility/licenses.md) registra uso, identidad, origen, licencia observada y pendientes. Incluye **16 paquetes del SDK, 17 dependencias Python, tres Actions**, herramientas host, referencias S01-S20 y Noesis/launchers. Los candidatos sin versión elegida continúan sin adopción; ninguna lectura de licencia se presenta como prueba de compatibilidad funcional.

La metadata del SDK no bastaba para la revisión: `custom` ocultaba textos Zlib en libctru/citro2d/citro3d y MPL-2.0 en el arranque 3DS; `None` en newlib y auxiliares exige investigar términos concretos. 3dstools/tex3ds presentan diferencias entre etiquetas y `COPYING`. En picasso, el `COPYING` instalado y el tag v2.7.2 coinciden y contienen MIT. La matriz conserva estos resultados y sus fuentes primarias.

LIC01-LIC09 definen responsable por rol, evidencia necesaria y trabajo dependiente. Los casos MFA Tool y sh3-nx siguen sin licencia global identificada en las fuentes revisadas; Noesis conserva EULA pendiente. La evaluación de fuentes exactas, objetos enlazados, excepciones, avisos y contenido de cada entrega permanece en Q14/LIC07 y F14. Esto también alcanza los binarios sintéticos que se pretendan compartir desde CI; el workflow remoto aún no se ha ejecutado.

Se actualizaron fuentes, decisiones, ticket detallado, backlog y guías de continuidad. La licencia propia Apache-2.0, el runtime, locks, workflow y datos del juego no se modificaron. No se instaló ninguna herramienta candidata ni se incorporó código recuperado.

## Método y entradas

1. Lectura de `CMakeLists.txt`, `scripts/build_3ds.sh`, el comando de enlace en `build/3ds/CMakeFiles/sh3_diagnostic.dir/link.txt`, manifiesto SDK, locks Python y workflow. El enlace observado selecciona las tres bibliotecas 3DS, libm y arranque/runtime por defecto; no es un mapa completo de objetos.
2. Consulta `dkp-pacman -Qi/-Ql` y lectura de archivos relevantes dentro de la imagen fijada. Contenedor `--read-only --network none --cap-drop ALL --security-opt no-new-privileges`, sin montajes del checkout/ISO. Sin cambios de paquetes.
3. Lectura local de metadata y licencias de distribuciones Python instaladas; contraste de colorama con el tag 0.4.6. Las versiones corresponden a la unión de ambos locks, incluidos transitivos.
4. Consultas HTTPS de solo lectura a fuentes primarias públicas: archivos de licencias, README, cabeceras, listados de repositorios y páginas oficiales. No se enviaron originales, credenciales ni archivos privados. Las respuestas con error no se usan como conclusión de licencia ausente.
5. Registro público compacto de URLs, referencias y hashes en [license-evidence.json](../compatibility/license-evidence.json). Los 43 documentos con snapshot incluyen textos y listados consultados, no 43 licencias distintas. Otras cuatro páginas oficiales se registran como referencias web sin snapshot. Un hash de licencia no fija el resto de un repositorio.

Identidad del SDK: `devkitpro/devkitarm@sha256:116afba8df8453961de2936ffab20dd441edf4d682856c1ec8b0e53d7ed0bbf5`. Host de revisión: Python 3.14.6 en `.venv`. El JSON de evidencia fija hashes de los locks, workflow, CMake, script de compilación, licencia propia y entradas locales de build. No hay commit nuevo; el trabajo permanece en el checkout.

Comando de consulta reproducible para metadata, desde la raíz:

```sh
rtk proxy docker run --rm --read-only --network none \
  --cap-drop ALL --security-opt no-new-privileges \
  devkitpro/devkitarm@sha256:116afba8df8453961de2936ffab20dd441edf4d682856c1ec8b0e53d7ed0bbf5 \
  dkp-pacman -Qi libctru citro2d citro3d 3dstools devkitarm-gcc \
  devkitarm-binutils devkitarm-newlib devkitarm-crtls 3ds-examples \
  picasso tex3ds 3ds-cmake devkitarm-cmake dkp-cmake-common-utils \
  dkp-toolchain-vars devkitarm-rules
rtk proxy .venv/bin/python -m tools.qa.check_repository
```

Las consultas de archivos y fuentes se conservan en `build/f00-06-sdk.json`, `build/f00-06-sdk-helpers.json`, `build/f00-06-python-licenses.json`, `build/f00-06-upstream.json` y los complementos `-extra`, `-followup`, `-headers`. Son evidencia local ignorada; el JSON público conserva solo metadata, URLs y hashes, no los textos completos ni código de terceros.

## Validación

La revisión corresponde al criterio de este ticket: inventario por componente y pendientes explícitos. La comprobación puntual compara los artefactos con las entradas efectivamente presentes; no se añade un framework de auditoría al producto.

| Comprobación | Esperado | Resultado |
|---|---|---|
| Paquetes Python | Coincidencia exacta de nombres/versiones con ambos locks y licencias documentadas | **Pasa**: 17/17 en locks, 16/16 instalados con versiones y hashes de licencias coincidentes; colorama upstream identificado |
| SDK y Actions | Versiones coinciden con manifiesto; tres commits coinciden con workflow | **Pasa**: 16/16 paquetes y 3/3 Actions |
| Documentos y archivos locales | Hashes de snapshots y entradas sin divergencias | **Pasa**: 43 documentos consultados y 11 entradas locales |
| Candidatos S01-S20 | Todos tienen origen, identidad/estado y licencia o pendiente | **Pasa**: 20/20 referencias y nueve pendientes con responsable/criterio |
| Caso normal y error | Zlib trazable; candidatos sin términos permanecen pendientes | Revisado en la matriz; no se ocultan LIC01-LIC09 |
| Arquitectura, custodia y trazabilidad EARS | Cero errores y enlaces locales válidos | **Pasa**: `Repository checks: PASS (0 errors)` |

Resultado de la comprobación puntual Python: `build/f00-06-inventory-check.json`. Se compararon conjuntos nombre/versión de locks, metadata instalada, lista de paquetes y referencias `uses`; se recalcularon SHA-256 de los textos capturados y entradas locales. La comprobación de S01-S20 verifica presencia; su significado y los casos normal/error se revisaron en la matriz. No se validó contenido privado ni el mapa final de enlace.

No se repitió la batería de 180 pruebas de F00.05 ni los builds C++/3DS porque solo cambia documentación y metadata de evidencia. Sus resultados históricos se conservan en sus informes. No hay nueva prueba en consola ni ejecución remota de CI.

Fuentes sin commit: `build/f00-06-source-manifest.json`, **12 archivos** de documentación y metadata pública; SHA-256 `7c178393cba776fd41396522a6b92a082983d92c7471b8093aca116262ef482d`. Excluye este informe para evitar autorreferencia y no contiene originales. Las entradas de compilación/locks se identifican por separado en `license-evidence.json`.

## Continuidad

F00.06 se cierra con el inventario inicial y sus límites; Q04/Q14 y LIC01-LIC09 conservan los trabajos que les corresponden. **G00 continúa abierta y la siguiente tarea es F00.07 — Registrar incógnitas y responsables**: consolidar Q01-Q14 con estado, rol, riesgo, evidencia de cierre y dependencia de puerta/ticket, incluyendo los hallazgos de esta revisión. El cierre de F00 no equivale a aprobar G01 ni la extracción o distribución de originales.
