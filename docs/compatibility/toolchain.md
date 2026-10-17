# Inventario inicial de herramientas

Fecha: 2026-10-16. Las versiones siguientes provienen de consultas ejecutadas, no de la propuesta original del PDF.

| Herramienta | Versión/identidad | Uso y evidencia |
|---|---|---|
| devkitPro devkitarm | Digest en `toolchains/devkitpro-image.txt` | Imagen oficial multiarquitectura; build 3DS aislado sin red |
| devkitARM | r68-1; GCC ARM 16.1.0 | C++17 compilado para ARM; no instalado globalmente en macOS |
| libctru | 2.7.0-1 | Adaptador de entrada/ciclo de vida/audio; compilación comprobada |
| citro2d | 1.7.0-1 | Patrón sintético; compilación comprobada |
| citro3d | 1.7.1-2 | Contexto/frame; compilación comprobada |
| 3dstools | 1.3.1-3 | Generación de 3DSX/SMDH |
| 3ds-examples | 20240917-1 | `simple_tri` construido dos veces desde fuentes limpias; igualdad de 3DSX/SMDH |
| picasso / general-tools | 2.7.2-3 / 1.4.4-1 | Ensamblado del shader e incorporación mediante `bin2s` en la comprobación del SDK |
| GNU Make del SDK | 4.3 | Receta oficial del ejemplo; licencia declarada GPLv3+ en `--version` |
| CMake host | 4.2.3; mínimo de proyecto 3.21 | Presets host y separación de targets |
| Apple Clang | 15.0.0 | Build host pasa; ASan de esta versión aborta en el host actual |
| LLVM Homebrew | 22.1.4 | Alternativa instalada para sanitizadores host |
| GCC Linux | 12.2.0 | Tests y cobertura portable dentro del contenedor |
| Python host | 3.14.6 | Venv local, fixtures y herramientas; mínimo de proyecto 3.11 |
| pytest/pytest-cov/gcovr/Ruff | Versiones directas en `requirements-dev.in`; transitivas y hashes en `requirements-dev.lock` | Entornos aislados; instalación con hashes |
| GitHub Actions | Commits fijados en `.github/workflows/ci.yml` | Referencias oficiales consultadas; ejecución remota pendiente |
| actionlint | 1.7.12, binario oficial con checksum contrastado | Validación local del workflow sin errores; no sustituye ejecución remota |

Procedencia: [devkitPro Dockerfiles](https://github.com/devkitPro/docker), [ejemplos 3DS](https://github.com/devkitPro/3ds-examples), [libctru](https://github.com/devkitPro/libctru), [citro2d](https://github.com/devkitPro/citro2d), [citro3d](https://github.com/devkitPro/citro3d). El inventario completo de paquetes de la compilación se conserva en `build/3ds/toolchain-packages.txt`.

[F01.01 completada](../execution/f01-01-toolchain.md): ejemplo oficial reproducible, probe C++17 ARM, build propio limpio y cinco casos de error del script. [Identidades y hashes](toolchain-check-evidence.json). Verificado localmente en Linux ARM64; ejecución de consola y CI remota pendientes. El nuevo chequeo es requisito previo del job 3DS y sus reportes se conservan sin subir fuentes/binarios del ejemplo.

F00.06 completó la [revisión inicial de procedencia y licencias](licenses.md), incluyendo runtime, herramientas host, auxiliares del SDK, dependencias Python, Actions y candidatos S01-S20. Las bibliotecas 3DS y el arranque pueden incorporarse al ejecutable; las herramientas host no se clasifican como código enlazado. La revisión del artefacto concreto y sus avisos permanece en Q14/F14. Ghidra, PCSX2, Noesis, MFA Tool, Blender y FFmpeg siguen sin adopción ni validación funcional local.

Los metadatos de `dkp-pacman -Qi` son una entrada de la revisión, no su conclusión. Los textos de libctru/citro2d/citro3d identifican Zlib; `3dsx_crt0.s` identifica MPL-2.0. 3dstools y tex3ds presentan diferencias entre metadata y `COPYING`; picasso tiene un texto MIT coincidente con su tag. Se documentan las diferencias y los pendientes LIC01-LIC09, sin asumir términos a partir de `custom` o `None`. [Hashes y fuentes consultadas](license-evidence.json).

## Inspección ISO adoptada

[pycdlib 1.22.0](https://pypi.org/project/pycdlib/1.22.0/) se usa solo en herramientas Python host, fijado con hashes en `requirements-tools.lock` e incluido en `requirements-dev.lock`. Metadatos de licencia: LGPL-2.1-only. [API oficial](https://clalancette.github.io/pycdlib/pycdlib-api.html): `open_fp`, `walk`, `get_record`, `open_file_from_iso`; se usa un stream local `rb`. Probado con ISO sintética y copia europea local, sin redistribuir la biblioteca en el ejecutable 3DS.

## F01.05: depurador y emulador

GDB ARM **14.1**, incluido en la imagen fijada: resolución estática y conexión real a Azahar comprobadas. Azahar **2126.2 ARM64** se ejecutó localmente en macOS 26.5/M2 desde su ZIP oficial identificado; versión/configuración/hash y límites en [evidencia](debugging-evidence.json) y [procedimiento](debugging.md). Breakpoints alcanzados; audio no disponible sin DSP y refresco parcial observado tras reconexión. No se declara estabilidad ni ejecución física. No se instaló en Applications ni se distribuye con el juego.
