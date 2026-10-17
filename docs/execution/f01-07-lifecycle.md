# F01.07 — ciclo de vida y controles reservados

Fecha: **2026-10-16**. Implementación local, batería de pruebas y build ARM **7c369f7e8c79** completados. **Tapa, HOME, escucha y retorno físicos pendientes; F01.07/G01 siguen abiertos.** Sin acceso a la ISO ni a datos originales.

[Ticket detallado](../specs/sh3-3ds/tasks/F01.md#f0107), [EARS L01-L10 y política](../compatibility/lifecycle-contract.md), [matriz manual H01-H12](../compatibility/lifecycle-probe.md).

## Resultado y alcance

`DiagnosticApp::step` ya no consulta entrada ni presenta mientras está suspendida. Una prueba nueva reprodujo antes del cambio que un input con quit detenía esa sesión; ahora queda suspendida hasta dispatch de plataforma. El host sintético también usa dispatch para despertar. No se cambió la tabla de estados del dominio: running, paused, suspended y stopped conservan su función.

Los hooks comparan estado anterior/final. Solo una transición real suspende audio o reinicia métricas; hooks duplicados o wake/restore fuera de una suspensión no añaden esos efectos. La salida es terminal, incluso si llegan otros hooks en el mismo lote. El ajuste de audio tras la reanudación ocurre al regresar al bucle y respeta pausa/mute. El callback no guarda archivos, libera recursos ni reconstruye servicios. RAII conserva el orden hook → audio → target GPU → Citro2D/Citro3D → gfx.

La entrada consulta down y held. Después de reanudar espera una lectura sin botones antes de aceptar una nueva pulsación; A/SELECT/X/Y/START residuales no activan acciones. También bloquea combinaciones que incluyan botones ajenos al diagnóstico, incluidos modificadores mantenidos antes de SELECT. Muestra `Release all buttons to enable controls` mientras corresponde. La prioridad normal sigue START > SELECT > Y > X > A. La salida de la pantalla de error gráfico reutiliza ese filtro.

La protección cubre combinaciones observadas con modificadores ajenos, incluido el combo predeterminado de Rosalina; no identifica configuraciones personalizadas del usuario. HOME/power permanecen en APT. No se modificó firmware, configuración CPU o launcher. La lógica de I/O existente sigue síncrona, fuera de callbacks; no se afirma persistencia ante pérdida de energía ni se inventan políticas de streaming/combate/partidas aún inexistentes.

## Evidencia de pruebas

| Validación | Resultado |
|---|---|
| Regresión previa | La prueba de app suspendida con input quit falló antes del cambio; `regression-before.log` |
| AppleClang 15 Debug | **47/47 CTest**, `host-debug-final.log` |
| AppleClang 15 Release/NDEBUG | **47/47 CTest**, `host-release.log` |
| LLVM 22.1.4 ASan + UBSan | **47/47**, sin hallazgos; `host-sanitize.log` |
| GCC 12.2 Linux ARM64, copia limpia | **47/47**, `clean-project/host-coverage.log` |
| Cobertura portable | **302/303 líneas (99.67 %)**, **219/224 ramas (97.77 %)** y **38/38 funciones** |
| ARM real, devkitARM r68/GCC 16.1 | **12 unidades C++**, ELF/3DSX/SMDH generados y bundle create/verify PASS |
| Python 3.14.6 | **227/227**; líneas **641/668 (95.96 %)** y ramas **260/274 (94.89 %)**, gate aprobado |
| Calidad | Ruff check/format (22 archivos), checks del repositorio (0 errores), actionlint, sintaxis Bash y clang-format pasan |
| Hardware / CI remota | No ejecutados |

Se mantienen los casos anteriores y se añaden diez escenarios de composición real con SDK/Tone controlados:

| Escenario | Demostración |
|---|---|
| lifecycle_home_running/paused/muted | Pares suspend/restore dentro de un mismo bombeo APT; estado, tono y opciones conservados |
| lifecycle_duplicate_hooks | Wake/restore no solicitado no borra ventana llena; duplicados de suspend/restore producen un único efecto |
| lifecycle_exit_batch | EXIT seguido de sleep/wakeup/suspend/restore/EXIT no consulta entrada ni presenta ni revive |
| lifecycle_close_suspended | APT devuelve false sin callback ONEXIT; cierre limpio sin procesar input pendiente |
| lifecycle_suspended_input | Iteraciones suspendidas con botones de pausa/página/guardado/salida no son consultadas |
| lifecycle_resume_keys | Botones nuevos/mantenidos al volver se ignoran hasta liberación y nueva pulsación; aviso visible en salida textual |
| lifecycle_reserved_chords | Modificador L+abajo previo impide interpretar SELECT y demás comandos; tras soltar todo, X/START funcionan |
| lifecycle_options_home | Opción guardada antes de HOME se conserva sin escritura adicional desde hooks |

La matriz de 25 transiciones del dominio se complementa con 10000 ciclos repetidos; no son 10000 ensayos físicos. El contrato de aplicación verifica cien pasos suspendidos sin poll/present y todos los eventos posteriores a stopped sin efectos. La prueba con log circular conserva solo cambios reales. El double de HID ahora indexa teclas por iteración APT, no por número de lecturas: saltarse poll ya no reproduce botones atrasados artificialmente. Los hooks por lotes representan la secuencia síncrona sleep/despertar; los hooks separados prueban una entrega adversa.

Los 47 casos pertenecen a los presets existentes; 39 llevan sdk-double. CMake registra los escenarios nuevos, por lo que Actions los recoge sin agregar jobs. Los checks se mantienen en Release. La cobertura sigue limitada a bibliotecas portables, sin contabilizar doubles o adapters 3DS como cobertura física. gcovr produjo XML/JSON y avisó que su opción genérica output no se utilizó al suministrar destinos explícitos. El primer build local de pruebas tuvo una referencia fuera de alcance en un helper de test; se corrigió y se conserva en `host-debug.log`. El log final y las restantes compilaciones pasan.

## Receta, archivos y versiones

Todos los reportes están en `build/f01-07/`. Comandos host: presets CMake Debug/Release/sanitize, build y CTest con JUnit. Sanitizadores con `/opt/homebrew/opt/llvm/bin/clang++`, `UBSAN_OPTIONS=halt_on_error=1:print_stacktrace=1`. Los JUnit se copiaron a `host-*-tests.xml` para no depender de futuras compilaciones en el directorio común.

ARM/GCC usaron `devkitpro/devkitarm@sha256:116afba8df8453961de2936ffab20dd441edf4d682856c1ec8b0e53d7ed0bbf5`, contenedor read-only sin red ni capacidades, tmpfs y copia sintética limpia. La venv Linux de gcovr fue montada solo en lectura. SDK: devkitARM r68-1, libctru 2.7.0-1, Citro2D 1.7.0-1 y Citro3D 1.7.1-2. Ejecutados `bash scripts/build_3ds.sh`, preset host-coverage, CTest y gcovr.

`clean-inputs.json`: **55 entradas**, SHA-256 `4550c949652cb0f959c7f5ab3cc67d7d83e2d87d8df89f99af3a4dba89dae8be`. Se comprueba correspondencia con los fuentes actuales. Logs y cobertura ARM/GCC en `clean-project/`; Python en `pytest.xml`, `python-coverage.xml/json`, `python-tests.log`. Fuentes/config/tests/docs quedan inventariados en `source-manifest.json`, excluyendo este informe por autorreferencia.

Archivos en `build/f01-07/artifacts/`:

| Archivo | Bytes | SHA-256 |
|---|---:|---|
| sh3_diagnostic.3dsx | 215924 | `6ae36ddfee92bf9eb2e648b0b13412e05dbb536765216905d14f2b3b53771115` |
| sh3_diagnostic.elf | 1863768 | `e98635a738949ab5f7ae7694178d2e8042e1458fa41382853c0b5a2e217422e1` |
| debug-bundle.json | 357 | `54b780cdee1ba276eab82ebf8a12053a4e4d80aedca9f04cf0839ab4ebbfabfd` |
| probe.txt | 16 | `b5ecd4976f9ee278f1a384e5d346f44797c531ea6b47b62d14ca48261d8cfc4a` |

SMDH, build-id, inventario de paquetes y SHA256SUMS también conservados; registro completo en `artifacts.json`. El build ID etiqueta los fuentes/CMake; hashes identifican cada binario. No se mezclaron símbolos con F01.06 ni se publicaron artefactos. LIC07 sigue pendiente antes de compartirlos; no se creó commit.

## Límites y siguiente tarea

No se ejecutó este build en Azahar ni en consola. Se priorizó probar las transiciones/control de efectos; la anomalía previa de entrada/captura del emulador no se declara resuelta. Contratos con dobles y compilación no acreditan escucha, tapa, HOME, colas DSP físicas, retorno al launcher ni estabilidad de treinta minutos. Tampoco cierran T11 del juego completo o los presupuestos Q08/Q13.

H01-H12 deja pasos y campos para la New Nintendo 2DS XL real; target.json conserva hardware_execution=not_tested y versiones desconocidas. La siguiente tarea independiente es **F01.08 — automatizar builds y diagnóstico de cierre**. Su parte local puede continuar; G01 requiere todavía las evidencias físicas pendientes.
