# Contrato de automatización — F01.08

Requisitos padre: RNF05.02, RNF03.01, RNF08.02, RNF04.01 y RNF11.05-RNF11.09. Este contrato concreta la aceptación local; no sustituye G01 físico.

## Requisitos EARS

- **B01 [E]** WHEN un preset de pruebas no descubre ningún test THEN CTest SHALL terminar con error.
- **B02 [E]** WHEN falla configuración, compilación, prueba o gate de cobertura THEN el job SHALL fallar y conservar los informes disponibles.
- **B03 [E]** WHEN termina el build 3DS THEN el verificador SHALL exigir los ocho archivos declarados, regulares, no vacíos y coherentes con el ID, bundle, fixture y checksums.
- **B04 [U]** El verificador SHALL limitar sus lecturas a nombres fijos del build y a entradas sintéticas explícitas; SHALL no ejecutar los binarios ni leer rutas indicadas por manifiestos.
- **B05 [E]** WHEN existe evidencia registrada THEN la creación SHALL fallar sin reemplazarla; una nueva compilación SHALL usar una carpeta limpia.
- **B06 [E]** WHEN se genera el informe de artefactos THEN este SHALL registrar ID, imagen SDK esperada y tamaño/SHA-256 de cada archivo. La verificación posterior SHALL exigir el recibo original intacto y coherente con esos mismos archivos e imagen. Su éxito SHALL acreditar consistencia de artefactos, sin afirmar ejecución en consola.
- **B07 [E]** WHEN se prepara el ensayo prolongado THEN el registro SHALL comenzar pendiente y exigir sesión física identificada, treinta minutos de actividad, checkpoints, salida y error simbolizado para evaluar G01.

## Diseño y límites

El shell orquesta compilación y propaga códigos de salida. `tools.debug.bundle` mantiene el contrato ELF/3DSX; `tools.qa.build_artifacts` compone ese verificador con comprobaciones del conjunto de distribución y emite un recibo exclusivo. Las pruebas inyectan fallos en herramientas y artefactos, sin SDK ni recursos originales. El dominio C++ no cambia ni depende de estos módulos.

Los ocho archivos son `sh3_diagnostic.3dsx`, `sh3_diagnostic.elf`, `sh3_diagnostic.smdh`, `probe.txt`, `build-id.txt`, `debug-bundle.json`, `SHA256SUMS` y `toolchain-packages.txt`. Se comprueban cabeceras básicas, no toda la estructura ejecutable. El recibo no es firma, prueba de procedencia criptográfica ni comparación reproducible entre máquinas. La imagen esperada se fija por digest; el job ejecuta esa imagen y conserva su inventario de paquetes. El ID corto identifica fuentes del runtime; el SHA-256 completo identifica cada artefacto.

Los presets fallan sin tests y limitan cada caso a 120 segundos salvo timeout específico menor. Los jobs conservan sus límites globales. GitHub Actions conserva informes durante 14 días; una ejecución remota no se considera realizada por revisar el YAML o ejecutar localmente sus comandos. Antes de compartir binarios sigue aplicando LIC07.

## Verificación

1. Ejecutar cada preset contra un proyecto vacío y contra una prueba deliberadamente fallida: ambos deben devolver error; una prueba válida debe pasar.
2. Ejecutar el build con herramientas simuladas que fallen en configuración, compilación o inventario; ninguna ejecución debe producir recibo de éxito.
3. Retirar/vaciar/enlazar cada archivo, mezclar ELF/3DSX, cambiar ID, fixture o checksums: el verificador debe fallar.
4. Construir SDK oficial y diagnóstico propios desde una copia sintética limpia; conservar logs, inventario y recibo. Ejecutar host y cobertura desde esa misma copia.
5. Completar por separado el [ensayo prolongado](diagnostic-soak.md). El ring de 120 muestras y los contadores no reconstruyen treinta minutos de historial.
