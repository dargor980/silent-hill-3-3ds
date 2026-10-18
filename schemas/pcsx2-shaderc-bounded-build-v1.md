# SB v1 — Build acotado de Shaderc

Complementa [SC01–SC08](pcsx2-shaderc-v1.md), unidad
`F02.07/origin/effective-mapping/instrumented-build/prerequisites/dependencies-shaderc/build-and-validate`.

## Decisión de capacidad

La reserva general de 20 GiB se aplicó a este grupo sin medir su alcance.
La preparación verificada ocupa unos 75 MB de fuentes de trabajo y el build
configurado unos 3,2 MB; el destino dispone de aproximadamente 19,1 GiB.
Esto no predice el tamaño final. Para evitar otro bloqueo por una reserva
genérica, se permite un intento vigilado y limitado a esta biblioteca.

Esta excepción sustituye **solo para este intento de Shaderc** la exigencia
de 20 GiB de SC03/IB02. No modifica el evaluador IB ni habilita Qt, MoltenVK,
el build completo PCSX2 o cualquier otra dependencia. No autoriza borrar
archivos ni ampliar límites automáticamente. SRC37 conserva la decisión y
mediciones anteriores; SRC38 registrará el resultado del intento acotado.

## Requisitos EARS

- **SB01 — Inicio.** ANTES del intento, el coordinador DEBERÁ verificar los
  insumos de SRC37 y disponer de al menos 18 GiB libres; DEBERÁ limitar a dos
  jobs, conservar prefijo/arquitectura/opciones y colocar temporales del
  compilador dentro del directorio medido.
- **SB02 — Vigilancia.** MIENTRAS compile, el coordinador DEBERÁ medir cada
  segundo el espacio libre y los bytes lógicos/asignados del directorio de
  build. SI el build supera 2 GiB o quedan menos de 16 GiB libres, DEBERÁ
  terminar el grupo de procesos creado por el coordinador y conservar el
  resultado fallido. No DEBERÁ instalarlo ni ampliar el límite por sí mismo.
- **SB03 — Evidencia.** CUANDO termine, el coordinador DEBERÁ registrar
  mediciones iniciales/finales, máximos/mínimos observados, intervalo, comandos,
  límites, resultado y hash de log. La vigilancia DEBERÁ declararse como
  muestreo, no como cuota de disco ni garantía de ausencia de picos entre muestras.
- **SB04 — Aceptación.** CUANDO el build termine sin exceder los límites,
  el procedimiento DEBERÁ ejecutar SC04–SC07 antes de aceptar la dependencia.
  Las siete pruebas preparadas DEBERÁN pasar antes y después de instalar.
- **SB05 — Continuidad.** CUANDO cierre la etapa, el procedimiento DEBERÁ
  repetir CMake PCSX2 y evaluar IB con la reserva general original de 20 GiB.
  El éxito del intento acotado no DEBERÁ presentarse como aprobación del build
  completo ni del mapa efectivo.

## Diseño y tareas

El coordinador privado mide capacidad y administra únicamente el proceso que
inicia; CMake construye; los fixtures ya definidos validan API y SPIR-V. No se
modifica código del runtime 3DS ni el gate puro. Los tests de capacidad del
coordinador son precondiciones y mediciones reales; no se afirma que se haya
provocado falta de disco para probar una terminación de emergencia.

1. Verificar hashes y registrar estado inicial (SB01).
2. Ejecutar build vigilado sin reemplazar logs previos (SB02/SB03).
3. Ejecutar fixtures, instalar solo tras éxito y repetir consumo (SB04).
4. Verificar fuentes, dylibs, símbolos, manifiestos y carga efectiva.
5. Repetir configuración PCSX2/gate y documentar siguiente unidad (SB05).
