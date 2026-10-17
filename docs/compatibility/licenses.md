# Procedencia y licencias: inventario inicial

Versión 1.0 · revisión 2026-10-16 · F00.06 · RNF05.01/RNF08.03. [Evidencia de ejecución](../execution/f00-06-provenance.md), [herramientas verificadas](toolchain.md) e [inventario de fuentes](sources.md).

La revisión inicial está completada: identifica procedencia, versión o referencia observada, finalidad y pendientes de las dependencias actuales y candidatos del PDF. **No equivale a aprobar una distribución**. Q04 conserva la validación de herramientas futuras y Q14 la revisión del artefacto concreto. La licencia Apache-2.0 del [repositorio](../../LICENSE) no sustituye los términos de terceros ni se extiende a originales, recursos o lógica recuperada del juego.

## Alcance y evidencia

Las identidades adoptadas son los locks Python, los commits de Actions y el digest de la imagen. Los candidatos sin versión seleccionada se identifican como tales: observar una rama actual y calcular el hash de su licencia no fija su código ni demuestra compatibilidad con la edición europea. [license-evidence.json](license-evidence.json) conserva URLs, versiones, etiquetas declaradas y hashes de documentos consultados; no contiene código de terceros ni bytes del juego y no es un SBOM del binario final.

Se consultaron 16 paquetes relevantes de la imagen, las 17 dependencias únicas de los dos locks y las tres Actions configuradas. El SDK incluye otros paquetes; su presencia en la imagen no constituye adopción por este proyecto. La lista completa queda en `build/3ds/toolchain-packages.txt`; antes de usar otro paquete se amplía este inventario y se prueba su función.

Actualización F01.01: [ejemplo oficial y chequeo C++17 compilados](../execution/f01-01-toolchain.md). Se añade `general-tools 1.4.4-1`, empleado por las reglas de shaders mediante `bin2s`, con metadata ISC y `COPYING` GPLv3 sin resolver en LIC01. La [evidencia del build](toolchain-check-evidence.json) registra versiones, fuentes y salidas actuales; `license-evidence.json` conserva el snapshot histórico de F00.06, incluido el workflow de esa revisión.

Estados usados: **en uso** significa empleado por el desarrollo o diagnóstico actual; **disponible** significa instalado en el SDK sin uso directo demostrado por este proyecto; **candidato** significa sin adopción; **entorno externo** significa software de la consola del usuario, sin incorporarlo al port. La compatibilidad funcional y la revisión de distribución se registran por separado.

## SDK y componentes del ejecutable

Imagen oficial: `devkitpro/devkitarm@sha256:116afba8df8453961de2936ffab20dd441edf4d682856c1ec8b0e53d7ed0bbf5`. La consulta de metadatos se ejecutó sin red, montajes ni escritura en el contenedor. El enlace observado usa `-specs=3dsx.specs`, `citro2d`, `citro3d`, `ctru` y `m`, además del runtime por defecto del compilador. La lista de objetos realmente incorporados se obtendrá antes de distribuir; no se deduce de todos los paquetes instalados.

| Componente y versión del paquete | Uso / licencia observada | Procedencia, evidencia y pendiente |
|---|---|---|
| libctru 2.7.0-1 | En uso, enlazado; Zlib | El paquete dice `custom`; [README v2.7.0](https://github.com/devkitPro/libctru/blob/v2.7.0/README.md) contiene los términos. Build sintético comprobado; prueba física pendiente |
| citro2d 1.7.0-1 | En uso, enlazado; Zlib | [LICENSE v1.7.0](https://github.com/devkitPro/citro2d/blob/v1.7.0/LICENSE); sustituye la etiqueta inespecífica `custom` del inventario inicial |
| citro3d 1.7.1-2 | En uso, enlazado; Zlib | [LICENSE v1.7.1](https://github.com/devkitPro/citro3d/blob/v1.7.1/LICENSE); mismas condiciones de revisión por artefacto |
| devkitarm-crtls 1.2.6-1 | Arranque del ejecutable; MPL-2.0 en `3dsx_crt0.s` | [Fuente v1.2.6](https://github.com/devkitPro/devkitarm-crtls/blob/v1.2.6/3dsx_crt0.s) y [specs](https://github.com/devkitPro/devkitarm-crtls/blob/v1.2.6/3dsx.specs); `custom` no describe esta obligación. LIC07 |
| devkitarm-newlib 4.6.0.20260123-5 | Runtime C/libm; múltiples términos por archivo | Metadatos sin URL/licencia; [COPYING.NEWLIB](https://sourceware.org/newlib/COPYING.NEWLIB) identifica varios titulares y condiciones. Falta vincular fuentes/parches del paquete y objetos usados: LIC03 |
| devkitarm-gcc 16.1.0-1, dentro de devkitARM r68-1 | Compilador host GPL-3.0-or-later; runtime requiere revisión aparte | `libgcc` y `libstdc++` tienen avisos GPL con [GCC Runtime Library Exception 3.1](https://github.com/gcc-mirror/gcc/blob/releases/gcc-16.1.0/COPYING.RUNTIME). Ver [condiciones de libstdc++](https://gcc.gnu.org/onlinedocs/libstdc++/manual/license.html); no inferir licencia del ejecutable solo de la del compilador. LIC07 |
| devkitarm-binutils 2.46.0-1 | En uso, herramientas host | Paquete [GNU binutils](https://www.gnu.org/software/binutils/) declara GPL-3.0-or-later, GPL-2.0-or-later, LGPL-3.0-or-later y LGPL-2.0-or-later. No se incorpora el conjunto de herramientas al ejecutable |
| 3dstools 1.3.1-3 | En uso, generación 3DSX/SMDH; licencia sin resolver | Metadata `ISC`, pero `COPYING` instalado es GPLv3. [Árbol v1.3.1](https://github.com/devkitPro/3dstools/tree/v1.3.1) sin licencia global identificada; los dos generadores examinados no resuelven la discrepancia. LIC01 |
| picasso 2.7.2-3 | En uso en la comprobación del ejemplo oficial F01.01; MIT observado | Metadata `GPL`; el `COPYING` instalado y [v2.7.2](https://github.com/devkitPro/picasso/blob/v2.7.2/COPYING) coinciden por SHA-256 y dicen MIT. No se asume que la etiqueta del paquete sea la licencia efectiva de cada archivo |
| general-tools 1.4.4-1 | En uso en F01.01, `bin2s`; discrepancia pendiente | [Origen declarado](https://github.com/devkitPro/general-tools); metadata `ISC` y `COPYING` instalado GPLv3. Identidad/hash en evidencia del build; LIC01 antes de empaquetar el generador |
| tex3ds 2.3.0-4 | Disponible, conversión de texturas; discrepancia pendiente | Metadata `ISC`; `COPYING` instalado es GPLv3 y coincide con el [COPYING upstream observado](https://github.com/devkitPro/tex3ds/blob/master/COPYING). Falta relacionar fuentes/parches y componentes del paquete: LIC02 |
| 3ds-examples 20240917-1 | Referencia de desarrollo; `simple_tri` compilado en F01.01 | Metadata `custom`; README instalado coincide por hash con el [README upstream observado](https://github.com/devkitPro/3ds-examples), con Public Domain Mark 1.0. Tres fuentes y el icono predeterminado identificados; no se certifica equivalencia de toda la rama ni aprobación de redistribución |
| 3ds-cmake 1.5.2-1 | En uso, configuración 3DS | Origen devkitPro, identidad fijada por imagen/paquete; metadata sin licencia. Incluye `3DS.cmake`; LIC09 |
| devkitarm-cmake 1.2.4-1 | En uso, configuración ARM importada por 3DS | Origen devkitPro; metadata sin licencia. Se conservaron hashes de scripts observados; LIC09 |
| dkp-cmake-common-utils 1.5.3-1 | En uso, utilidades y plataforma CMake | Origen devkitPro; metadata sin licencia; LIC09 |
| dkp-toolchain-vars 1.0.5-1 | Disponible, auxiliares del entorno SDK | Origen devkitPro; metadata sin licencia; LIC09 |
| devkitarm-rules 1.6.0-4 | Disponible, reglas del SDK | [Origen](https://github.com/devkitPro/devkitarm-rules); metadata `custom`, términos concretos pendientes; LIC09 |

Los hashes de `COPYING` permiten reproducir las comparaciones: picasso `fff319f39e5a79efa71c837e4e901ad4a1ff432dd89d04febf0453a356911fd3`; 3dstools `3972dc9744f6499f0f9b2dbf76696f2ae7ad8af9b23dde66d6af86c9dfb36986`; tex3ds `8ceb4b9ee5adedde47b31e975c1d90c73ad27b6b165a1dcd80c7c545eb65b903`. Una etiqueta `None`, `custom` o una consulta API sin resultado no demuestra ausencia de restricciones.

## Herramientas host y CI

| Herramienta / identidad | Origen y términos observados | Estado y límite |
|---|---|---|
| CMake 4.2.3 host | [LICENSE.rst v4.2.3](https://github.com/Kitware/CMake/blob/v4.2.3/LICENSE.rst), BSD-3-Clause y avisos de terceros | En uso, generación de builds; no incluido en entregables 3DS |
| Python 3.14.6 host | [LICENSE v3.14.6](https://github.com/python/cpython/blob/v3.14.6/LICENSE), PSF e historial/terceros | En uso; CI configura 3.13.7 por separado. No se distribuye un intérprete |
| LLVM 22.1.4 host | [LICENSE.TXT](https://github.com/llvm/llvm-project/blob/llvmorg-22.1.4/llvm/LICENSE.TXT), Apache-2.0 con excepciones LLVM y terceros | En uso para sanitizadores; no implica incorporar todo LLVM al port |
| Apple Clang 15.0.0 / GCC Linux 12.2.0 | Distribuciones de herramientas del host; origen y builds en [fundación](../execution/foundation.md) | No se empaquetan; términos exactos del paquete Apple y componentes del contenedor host pendientes si se propusiera redistribuirlos, LIC08 |
| Docker y utilidades del host | Entorno que ejecuta la imagen fijada | No son dependencias enlazadas ni se distribuyen. El digest identifica el SDK, no la versión de Docker Desktop ni sus términos; LIC08 si se empaqueta ese entorno |
| actionlint 1.7.12 | [rhysd/actionlint LICENSE.txt](https://github.com/rhysd/actionlint/blob/v1.7.12/LICENSE.txt), MIT | Validación local del workflow; binario oficial contrastado en fundación |
| actions/checkout `11d5960a326750d5838078e36cf38b85af677262` | [LICENSE fijado](https://github.com/actions/checkout/blob/11d5960a326750d5838078e36cf38b85af677262/LICENSE), MIT | Configurada; CI remota sin ejecutar |
| actions/setup-python `a26af69be951a213d495a4c3e4e4022e16d87065` | [LICENSE fijado](https://github.com/actions/setup-python/blob/a26af69be951a213d495a4c3e4e4022e16d87065/LICENSE), MIT | Configurada; Python del runner separado del host |
| actions/upload-artifact `ea165f8d65b6e75b540449e92b4886f43607fa02` | [LICENSE fijado](https://github.com/actions/upload-artifact/blob/ea165f8d65b6e75b540449e92b4886f43607fa02/LICENSE), MIT | Configurada para reportes y diagnóstico; no publica releases. Compartir binarios, también de CI, requiere LIC07 |

Las licencias de las Actions se refieren a sus repositorios; no sustituyen las de sus dependencias o las condiciones del servicio. Los runners hospedados no están fijados por digest. La revisión no presenta esta configuración como una ejecución remota comprobada.

### Python: dependencias directas y transitivas

La unión de `requirements-dev.lock` y `requirements-tools.lock` contiene estas **17 versiones únicas**, fijadas con hashes de distribución. Se leyeron los archivos de licencia de 16 paquetes instalados en `.venv`; `colorama` es condicional para Windows y se contrastó con su tag upstream. Los enlaces PyPI identifican el origen del paquete; las rutas y hashes de los textos efectivamente leídos están en `python_packages` del JSON de evidencia.

| Paquete | Versión | Términos observados | Uso |
|---|---|---|---|
| [colorama](https://pypi.org/project/colorama/0.4.6/) | 0.4.6 | BSD-3-Clause; [texto fijado](https://github.com/tartley/colorama/blob/0.4.6/LICENSE.txt) | QA, condicional Windows, no instalado en este host |
| [colorlog](https://pypi.org/project/colorlog/6.12.0/) | 6.12.0 | MIT | QA transitivo |
| [coverage](https://pypi.org/project/coverage/7.16.2/) | 7.16.2 | Apache-2.0; incluye NOTICE | Cobertura Python |
| [gcovr](https://pypi.org/project/gcovr/8.6/) | 8.6 | BSD-3-Clause | Cobertura C++ host |
| [iniconfig](https://pypi.org/project/iniconfig/2.3.1/) | 2.3.1 | MIT | QA transitivo |
| [jinja2](https://pypi.org/project/jinja2/3.1.6/) | 3.1.6 | BSD-3-Clause | Reportes transitivos |
| [lxml](https://pypi.org/project/lxml/6.1.3/) | 6.1.3 | BSD-3-Clause para lxml; términos adicionales en `LICENSES.txt` | Reportes transitivos; LIC08 |
| [markupsafe](https://pypi.org/project/markupsafe/3.0.4/) | 3.0.4 | BSD-3-Clause | Reportes transitivos |
| [packaging](https://pypi.org/project/packaging/26.3/) | 26.3 | Apache-2.0 **OR** BSD-2-Clause | QA transitivo |
| [pluggy](https://pypi.org/project/pluggy/1.7.0/) | 1.7.0 | MIT | QA transitivo |
| [pycdlib](https://pypi.org/project/pycdlib/1.22.0/) | 1.22.0 | LGPL-2.1-only | Inspector ISO host; no enlace 3DS |
| [pygments](https://pypi.org/project/pygments/2.21.0/) | 2.21.0 | BSD-2-Clause | QA transitivo |
| [pytest](https://pypi.org/project/pytest/9.1.1/) | 9.1.1 | MIT | Tests host |
| [pytest-cov](https://pypi.org/project/pytest-cov/7.1.0/) | 7.1.0 | MIT | Cobertura Python |
| [pyyaml](https://pypi.org/project/pyyaml/6.0.3/) | 6.0.3 | MIT | QA/lectura de YAML |
| [ruff](https://pypi.org/project/ruff/0.17.1/) | 0.17.1 | MIT para el proyecto; revisar dependencias del binario si se empaqueta | Lint y formato |
| [tomli](https://pypi.org/project/tomli/2.5.0/) | 2.5.0 | MIT | QA transitivo |

Los términos de lxml incluyen componentes con otras licencias y sus wheels pueden incorporar iconv (LGPL-2.1), zlib y bibliotecas XML/XSLT, entre otros. No se clasifica el wheel completo como BSD por su etiqueta principal. Ningún paquete Python está enlazado al ejecutable 3DS. Un instalador futuro que incluya estos paquetes necesitará revisar sus binarios y avisos exactos, LIC08.

## Candidatos y referencias del PDF

En las filas sin paquete instalado, **versión adoptada: ninguna**. `main/master` identifica solo el documento observado el 2026-10-16; la licencia global de un repositorio no acredita todos sus archivos ni la titularidad de código recuperado. La validación de formatos europeos con fixtures y casos reales privados sigue en F02-F04.

| Referencia | Componente / identidad observada | Procedencia y licencia inicial | Estado / condición de adopción |
|---|---|---|---|
| S01, S02 | memory-of-alessa, rama main | [LICENSE MIT](https://github.com/dreamingmoths/memory-of-alessa/blob/main/LICENSE) | Referencia de investigación NTSC-U; no incorporado. Verificar procedencia por módulo y diferencias con Europa antes de reutilizar lógica |
| S03 | 3ds-examples 20240917-1 | Inventario SDK anterior | `simple_tri` compilado dos veces en F01.01; ejecución física y distribución no verificadas |
| S04, S09 | libctru 2.7.0-1 / NDSP | Inventario SDK anterior, Zlib | En uso; compilación observada, consola pendiente |
| S05 | citro3d 1.7.1-2 | Inventario SDK anterior, Zlib | En uso; no certifica rendimiento de juego |
| S06 | citro2d 1.7.0-1 | Inventario SDK anterior, Zlib | En uso en diagnóstico sintético |
| S07 | tex3ds 2.3.0-4 | Inventario SDK anterior | Disponible; no hay conversión de originales; LIC02 antes de adoptar su receta |
| S08 | picasso 2.7.2-3 | Inventario SDK anterior, MIT observado | Utilizado por el shader del ejemplo oficial F01.01; validar por separado recetas del motor |
| S10 | Ghidra + ghidra-emotionengine-reloaded, ramas master/main | [Ghidra Apache-2.0](https://github.com/NationalSecurityAgency/ghidra/blob/master/LICENSE) y [plugin Apache-2.0](https://github.com/chaoticgd/ghidra-emotionengine-reloaded/blob/main/LICENSE) | Candidatos. Fijar par de versiones compatible y dependencias Java; probar análisis en F04. No equiparar licencia de Ghidra con la del resultado recuperado |
| S11 | PCSX2 v2.8.2, paquete oficial macOS | [COPYING.GPLv3 fijado](https://github.com/PCSX2/pcsx2/blob/v2.8.2/COPYING.GPLv3), texto GPLv3; fuentes consultadas GPL-3.0+ | Instalado como herramienta host externa; firma/notarización y perfil comprobados. BIOS principal aportada por el usuario y arranque comprobados por logs; captura pendiente. [Evidencia actual](ps2-boot-evidence.json); sin redistribución |
| S12 | MFA Tool for Silent Hill 3 PS2, commit `6c362d2c163236c0496c42ed297eb9c07487ab69` (`main`) | [Repositorio y README](https://github.com/RayneDuarte/MFA-Tool-for-Silent-Hill-3-PS2-); sin licencia global identificada; acredita script BMS de aluigi | **No adoptado tras evaluación F02.02**, LIC04 sigue abierto para adopción/copia; [evidencia fijada](mfa-candidate-evidence.json). Sondeo propio con procedencia atribuida, sin equivalencia ni extracción acreditadas |
| S13 | Sparagas/Silent-Hill, rama main | [LICENSE MIT](https://github.com/Sparagas/Silent-Hill/blob/main/LICENSE) | Plugins candidatos; revisar cada plugin y compatibilidad. La licencia de Noesis es independiente, LIC06 |
| S14 | Azahar, rama master | [LICENSE.txt](https://github.com/azahar-emu/azahar/blob/master/LICENSE.txt), texto GPLv3 | Binario oficial ARM64 2126.2 fijado y ensayado localmente en F01.05; hash/procedencia en [registro](debugging-evidence.json). Uso host, sin redistribución; revisión de componentes/avisos para distribuir sigue pendiente |
| S15 | Luma3DS/Rosalina, rama master | [LICENSE](https://github.com/LumaTeam/Luma3DS/blob/master/LICENSE), texto GPLv3 | Entorno posible de depuración; versión/instalación del usuario no confirmadas. No se redistribuye firmware |
| S16 | 3dbrew, NCCH Extended Header | [Referencia técnica](https://3dbrew.org/wiki/NCCH/Extended_Header) | Documentación, sin código incorporado; revisar licencia de página/fragmentos si se propone copiarlos |
| S17 | sh3-nx, rama main | [Repositorio y README](https://github.com/cutarev/sh3-nx); sin licencia global identificada en el árbol revisado | Referencia arquitectónica de otra plataforma; LIC05 antes de reutilizar. Las licencias citadas para subcomponentes no cubren todo el repositorio |
| S18 | PS2Recomp, rama main | [LICENSE](https://github.com/ran-j/PS2Recomp/blob/main/LICENSE), texto GPLv3 | Candidato experimental; fijar alcance, runtime y términos del código generado antes de una prueba; no es la base adoptada del port |
| S19 | Blender, rama main | [COPYING](https://github.com/blender/blender/blob/main/COPYING) y [texto GPLv2](https://github.com/blender/blender/blob/main/doc/license/GPL-license.txt) | Candidato host; versión/addons y receta de transformación pendientes |
| S20 | FFmpeg, sin build seleccionado | [Términos oficiales](https://ffmpeg.org/legal.html): LGPL-2.1-or-later; componentes opcionales GPL alteran el resultado | Candidato host, sin codecs ni flags elegidos; conservar configuración, dependencias y licencia efectiva antes de adoptar |
| Adicional | Noesis, referencia pública 4.474 | [Distribución oficial de Rich Whitehouse](https://richwhitehouse.com/index.php?content=inc_projects.php&showproject=91); EULA no verificada | **Pendiente de adopción**, LIC06. No se descargó ni ejecutó el binario |
| Entorno | Homebrew Launcher / 3ds-hbmenu, rama master | [README](https://github.com/devkitPro/3ds-hbmenu), permiso de reutilización con crédito y términos separados de dependencias | Launcher confirmado por el usuario; versión concreta pendiente. Se cita como entorno externo, no se incorpora al port |
| Entorno | FBI, rama master | [LICENSE.txt MIT](https://github.com/Steveice10/FBI/blob/master/LICENSE.txt) | Disponibilidad confirmada por el usuario; versión pendiente. Ruta CIA futura, sin generar ni instalar CIA |

«Texto GPLv2/GPLv3» describe el archivo leído. La variante `-only` o `-or-later` y sus excepciones se determinarán con los avisos del código de la versión finalmente seleccionada; no se infieren del apéndice genérico de la licencia.

## Pendientes con criterio de cierre

Los responsables son roles de mantenimiento, no personas adicionales contratadas. Cada pendiente limita el componente o publicación señalados; no impide continuar documentación ni pruebas sintéticas independientes.

| ID | Responsable y trabajo concreto | Evidencia de cierre | Limita |
|---|---|---|---|
| LIC01 | Mantenedor: resolver ISC/GPLv3 de 3dstools 1.3.1-3 y general-tools 1.4.4-1, añadido en F01.01 | Receta/fuentes de cada paquete exacto, avisos de cada generador y explicación verificable de su `COPYING` | Empaquetar/redistribuir las herramientas; revisión de procedencia de sus salidas en LIC07 |
| LIC02 | Responsable del pipeline: verificar tex3ds y sus dependencias | Fuentes/parches del paquete, términos efectivos y prueba reproducible de conversión con fixture | Adopción de receta F03 y redistribución de tex3ds |
| LIC03 | Mantenedor: completar newlib de devkitARM | Fuentes y parches exactos, mapa de enlace y términos de archivos incorporados | Revisión de binario 3DS; no declarar el paquete libre de condiciones por metadata `None` |
| LIC04 | Investigador de assets: esclarecer MFA Tool y antecedente BMS | Permiso/licencia verificable para el código concreto y sus derivados, o seleccionar implementación propia con procedencia documentada | Adopción/copia de esa herramienta F02 |
| LIC05 | Investigador de comportamiento: esclarecer sh3-nx | Licencia y procedencia del módulo propuesto, o mantenerlo solo como referencia | Incorporación de código F04; no afecta la ruta PS2 definida |
| LIC06 | Responsable del pipeline: revisar Noesis y plugins por separado | EULA de versión seleccionada y licencia de cada plugin; prueba de formatos europeos | Adopción del flujo Noesis F02/F03 |
| LIC07 | Responsable de publicación: preparar el artefacto exacto | Inventario de objetos/libs/recursos, avisos, fuentes correspondientes cuando apliquen y comprobación de condiciones de las excepciones | Compartir binarios de diagnóstico/CI o release; G14 para distribución final |
| LIC08 | Mantenedor/QA: revisar un eventual paquete de herramientas host | Versiones/bundles exactos, avisos y dependencias de wheels, binarios, intérprete, imagen o entorno que se pretenda incluir | Solo empaquetado/redistribución de ese entorno; no se ha propuesto incluirlo en el port |
| LIC09 | Mantenedor: completar términos de auxiliares devkitPro | Repositorio/receta y licencia de versiones concretas de los cinco paquetes auxiliares | Copiar o redistribuir esos scripts/SDK; su uso actual está identificado, revisión de términos pendiente |

LIC07 incluye el arranque MPL-2.0: comprobar correspondencia entre fuente y objeto, conservar avisos e informar cómo obtener el código cubierto cuando se distribuye el ejecutable, conforme a las [secciones 3.1–3.4 de MPL-2.0](https://www.mozilla.org/en-US/MPL/2.0/). La excepción de GCC también tiene condiciones; su presencia no exime de revisar el resto del binario.

El workflow existente selecciona reportes y un diagnóstico sintético, pero todavía no adjunta el conjunto de avisos/fuentes correspondiente. **No hay publicación revisada por esta tarea**: antes de compartir esos binarios se completa LIC07 y se ajusta el empaquetado necesario. Esta observación no cambia el runtime, las pruebas ni los locks, y no convierte los datos originales en artefactos publicables.

Para incorporar una dependencia nueva: registrar versión/commit, origen, términos y modificaciones; decidir si se ejecuta en host, se enlaza o se distribuye; probar su contrato con fixtures; actualizar esta matriz y la evidencia. Una fuente incierta conserva estado pendiente. La revisión de F00.06 se cierra al dejar ese estado explícito, mientras F14 revisará cada entrega concreta.

Actualización F02.02 (2026-10-17): la rama por defecto observada de S12 es `main`; sustituye la mención inicial `master`, que no fijaba una versión. Se conservaron hashes de cinco fuentes examinadas y el árbol de ese commit; la API informó licencia nula y no se identificó licencia global. Se eligió un sondeo propio, sin copiar ni ejecutar fuentes/binarios externos. El BMS publicado actualmente bajo el nombre Silent Hill 3 describe otra disposición y no confirma el antecedente exacto MFA. [Decisión y límites](../execution/f02-02-mfa-candidate.md). LIC04 sigue aplicando a una futura adopción del candidato; no se declara resuelta la licencia de ese código por haber elegido otra implementación.

Actualización F02.07/formato-camera (2026-10-17): se consultó memory-of-alessa `89c61883dd2ad5390223ba37d9bbacc62783d371` (LICENSE declara MIT) y sh3redux `50d10aef1b9afbfbf2ae5946a511a2c5e0a2f106` (texto GPLv3) para investigar estructuras/limitaciones. [Hashes y finalidad](camera-research-evidence.json). No se copiaron ni ejecutaron esos componentes; el sondeo Python es propio con atribución de la investigación de formato, sin afirmar clean room. Una licencia global del repositorio no se extiende por inferencia a los datos del juego o a cada insumo de decompilación; cualquier futura adopción requiere revisar sus archivos concretos. No se añade dependencia o autorización de distribución por esta consulta.

Actualización F02.07/camera-consumer-eu (2026-10-17): consulta documental de gABI y MIPS/binutils `9decc44bc67d9fb4248c2afe4fde77174e8abf80`. Las cabeceras de `mips-opc.c` y `mips-dis.c` declaran GPLv3 o posterior; el COPYING raíz leído contiene GPLv2 y no se usa para sustituir la declaración de los archivos. [Procedencia y hashes](camera-consumer-research-evidence.json). No se copió ni ejecutó código externo, no se añadió dependencia y no se afirma clean room. La implementación propia utiliza codificaciones/estructuras documentadas; no concede licencia sobre el ejecutable o recursos del juego.

Actualización F02.07/camera-pointer-origin-eu (2026-10-17): se revalidaron los hashes de las fuentes primarias MIPS/binutils ya fijadas para consultar efectos de registros, transferencias y formas escalares COP1/R5900. [Procedencia](camera-pointer-research-evidence.json). Continúa la declaración GPLv3 o posterior de los archivos consultados; no se incorporó o ejecutó su implementación, ni se añadieron dependencias o licencia sobre los datos del juego. No se afirma clean room.

Actualización F02.07/camera-caller-boundary-eu (2026-10-17): referencias MIPS fijadas revalidadas localmente para el análisis propio de transferencias y slots, sin nueva dependencia, adopción ni ejecución externa. Se mantienen las declaraciones GPLv3 o posterior y la ausencia de afirmación clean room. [Procedencia](camera-boundary-research-evidence.json), [alcance](../execution/f02-07-camera-boundary.md).

Actualización F02.07/camera-runtime-observation-plan-eu (2026-10-17): PCSX2 oficial **v2.8.2 macOS**, instalado por petición del usuario como herramienta host externa. Descarga contrastada con digest de release y firma/notarización verificadas; CLI y perfil privado comprobados, BIOS/juego/depurador en ejecución pendientes. Se consultaron fuentes fijadas de configuración con cabecera GPL-3.0+ y el texto COPYING.GPLv3, sin incorporar ese código al port. [Procedencia exacta](camera-observation-research-evidence.json), [resultado](../execution/f02-07-camera-observation.md). No se distribuye PCSX2; revisión de avisos/componentes del bundle necesaria si se propusiera empaquetarlo (LIC08). No se afirma clean room ni licencia sobre BIOS/originales.

Actualización F02.07/effective-mapping (2026-10-17): [SRC30](effective-mapping-evidence.json)
fija PCSX2 `fd9d310ccbb6b8b62c976da8886a3c8fd3a10ff3`, ocho fuentes/recetas y
`COPYING.GPLv3`. Las cabeceras de `vtlb.h` y `MemoryTypes.h` declaran GPL-3.0+.
Se consultaron los hechos de ABI y la configuración de compilación; el validador
es propio, sin copiar funciones del emulador ni añadir una dependencia al port.
No se afirma clean room. La receta de dependencias no se ejecutó. El futuro
build instrumentado será una herramienta host separada con fuentes, cambios y
avisos conservados; la revisión de dependencias/redistribución sigue en LIC08.

Actualización F02.07/instrumented-build (2026-10-17): [SRC31](pcsx2-build-evidence.json)
conserva checkout limpio del mismo commit oficial, su `COPYING.GPLv3` y un plan
de 25 descargas con hashes esperados de la receta. Se ejecutó CMake del checkout
primero hasta el fallo en PNG y después hasta JPEG. Se compiló e instaló un
piloto privado de libpng 1.6.58 con el parche APNG fijado: ambos archivos se
verificaron por hash, las 37 pruebas CTest pasaron y se conservó `LICENSE`
(PNG Reference Library License version 2) junto a las fuentes modificadas.
La receta completa no se ejecutó ni se generó un build de PCSX2. Los fixtures
C++20/Metal son propios. La revisión de términos individuales y de cualquier
bundle permanece en LIC08; no se redistribuye esta dependencia host.

Actualización de dependencias host (2026-10-17): [SRC32](pcsx2-dependencies-evidence.json)
registra fuentes y hashes de los avisos de este lote, conservados junto al build
privado. Las bibliotecas se usan en el emulador de investigación; no se añaden
al runtime 3DS ni se publica un bundle.

| Componente fijado | Avisos revisados | Alcance de este lote |
|---|---|---|
| NASM 3.02 | `LICENSE`, BSD-2-Clause | Herramienta host ARM64; produce objetos propios x86_64 |
| libjpeg-turbo 3.2.0 | `LICENSE.md` y `README.ijg`: IJG, BSD modificada y avisos subordinados descritos por el proveedor | JPEG/TurboJPEG x86_64, fuentes y avisos conservados; no se reduce el conjunto a una sola licencia |
| Zstd 1.5.7 | `LICENSE`, BSD de tres cláusulas | Biblioteca host; pruebas seleccionadas del proveedor conservadas |
| LZ4 1.10.0 | `LICENSE`, `lib/LICENSE` y `tests/COPYING` | Biblioteca BSD-2-Clause; programas de prueba GPL-2.0-or-later según avisos. La licencia de la biblioteca no se atribuye a todo el repositorio |
| WebP 1.6.0 | `COPYING` (BSD de tres cláusulas) y `PATENTS` | Bibliotecas host, con el aviso adicional de patentes conservado |

Los fixtures de esta etapa son propios. Los términos de las dependencias
subordinadas y de un eventual paquete completo siguen dentro del alcance de
LIC08; esta verificación local no constituye una revisión de redistribución.

Actualización SDL3 host (2026-10-17): [SRC33](pcsx2-sdl3-evidence.json) fija
SDL 3.4.12 y verifica su archivo oficial, `LICENSE.txt` (aviso de estilo zlib)
y los 2.183 archivos regulares de fuente sin cambios. Se conservan origen,
avisos subordinados y configuración; la biblioteca compartida y el auxiliar de
tests se instalan únicamente en el prefijo privado. Los cuatro casos C++ y su
proyecto CMake son propios y usan API públicas; no incorporan SDL al runtime
3DS. No se redistribuye el bundle; LIC08 conserva la revisión de dependencias
internas y avisos para ese eventual artefacto.

Actualización FreeType/HarfBuzz host (2026-10-17):
[SRC34](pcsx2-fonts-evidence.json) conserva fuentes, avisos y hashes exactos.

| Componente fijado | Avisos revisados | Uso |
|---|---|---|
| FreeType 2.14.3 | `LICENSE.TXT`, `docs/FTL.TXT`, `docs/GPLv2.TXT`; avisos BDF/PCF/gzip conservados | Biblioteca host; ofrece FTL o GPLv2-or-later. No se reduce el conjunto de avisos a una licencia global |
| HarfBuzz 14.2.0 | `COPYING`, Old MIT; `test/COPYING` y avisos subordinados conservados | Cuatro bibliotecas host; las fuentes tipográficas externas del proveedor no se usan en los fixtures propios |
| FontTools 4.60.1 | Wheel PyPI fijado por SHA-256; `LICENSE` MIT y `LICENSE.external` conservados | Generador host aislado en `build/`, sin instalación global ni enlace al objetivo |

El generador y los casos de API son propios; la fuente de rectángulos también
es original y usa la licencia Apache-2.0 del repositorio. No contiene contornos
ni textos de fuentes ajenas o del juego. No se incorporan dependencias al
runtime 3DS ni se publica un bundle; LIC08 conserva su revisión de una eventual
redistribución y sus avisos/créditos concretos.

Actualización PlutoVG/PlutoSVG host (2026-10-17):
[SRC35](pcsx2-pluto-evidence.json) fija y verifica PlutoVG 1.3.2 y PlutoSVG 0.0.7.
Ambos conservan su `LICENSE` MIT, fuentes y avisos completos. PlutoVG incluye
siete archivos `plutovg-ft-*` derivados de FreeType que citan FTL, y tres
headers `plutovg-stb-*` con alternativas MIT/dominio público; el aviso raíz
no sustituye los de esos archivos. Se registran sus hashes y la FTL íntegra
conservada en SRC34. No se modificaron fuentes ni se redistribuye el bundle;
LIC08 conserva la revisión de términos, créditos y fuentes de la entrega.

Los SVG, generador y fixtures son propios bajo Apache-2.0 del repositorio.
Se reutiliza FontTools 4.60.1 de SRC34 únicamente en host para añadir una tabla
SVG a la fuente geométrica propia. El fixture usa los hooks de la biblioteca
PlutoSVG instalada y API públicas, sin copiar el adaptador header-only al
repositorio ni incorporar dependencias al runtime 3DS.
