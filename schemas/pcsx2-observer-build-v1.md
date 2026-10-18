# Build instrumentado PCSX2 — OBT01–OBT07

Amplía [BB](pcsx2-baseline-v1.md) y [OB](pcsx2-observer-v1.md).
Unidad: `instrumented-build/build-and-validate`.

- **OBT01:** WHEN se prepare el build THEN SHALL verificar el manifiesto completo
  SRC50 o su revisión identificada tras una prueba fallida, y sus siete
  archivos propios; SHALL conservar baseline/prefijo y exigir
  al menos 20 GiB antes de la compilación completa. Un checkout modificado
  SHALL admitirse solo si coincide exactamente con el parche identificado.
- **OBT02:** WHEN compile THEN SHALL usar una etapa nueva, observador ON,
  Qt, x86_64/macOS 11, Apple Clang/Metal explícitos, dos jobs, límite de etapa
  8 GiB, suelo 10 GiB y plazo 45 min, conservando logs y fallos según BB.
- **OBT03:** WHEN enlace THEN SHALL comprobar identidad del ejecutable y
  presencia del observador, y ejecutar los 113 tests originales sin cambios.
- **OBT04:** WHEN empaquete THEN SHALL conservar el bundle original, verificar
  ID/RPATH, arquitectura, recursos y firma ad hoc/entitlements del candidato;
  SHALL probar el candidato exacto con perfil nuevo y sin juego.
- **OBT05:** WHEN pruebe PINE THEN SHALL usar socket Unix privado, un cliente,
  plazo total acotado, recepción exacta y límite de 4.333 bytes. IF el transporte
  falla, se trunca o agota el plazo THEN SHALL cerrar el socket y rechazarlo.
- **OBT06:** WHEN valide el transporte real THEN SHALL contrastar versiones,
  framing, petición inválida y rechazo sin VM; SHALL verificar reconexión y
  cierre limpio. IF falla la protección contra SIGPIPE de un socket aceptado
  THEN SHALL cerrarlo antes de escribir; una desconexión temprana SHALL NOT
  terminar el emulador. Ninguna respuesta de error SHALL contarse como captura real.
- **OBT07:** WHEN publique THEN SHALL registrar solo metadatos depurados y
  mantener pendientes el coordinador OB07–OB08, la sesión MP08 y el hardware.

## Diseño y aceptación

Se reutiliza el supervisor probado de BB y el lector estricto OB. Un puerto
mínimo de socket y reloj permite probar recepción fragmentada, cierre, error
y deadline sin PCSX2. La conexión privada limita cada operación por el plazo
restante, no por un timeout que se reinicie en cada fragmento. Los paquetes se
validan aparte: el transporte no interpreta RAM ni publica bytes.

El coordinador local fija rutas y perfil. Para probar sin VM se usa una
petición sintética: el reply esperado es `OBSERVER_PAUSE`, con snapshots y
payload vacíos. Un request inválido debe rechazarse antes de encolarse al CPU.
La ausencia de VM permite probar el protocolo sin arrancar BIOS o juego.
El timeout del cliente no acredita por sí mismo el timeout interno del CPU.

Configurar y verificar son operaciones pequeñas con suelo 10 GiB; solo el
build completo exige 20 GiB iniciales. Se pueden retirar objetos intermedios
reconstruibles de pruebas propias tras inventariarlos; fuentes, ejecutables,
logs, informes y artefactos privados históricos se conservan.

Una reparación incremental del transporte conserva la fuente anterior, el
parche, bundle y recibos fallidos. Puede reutilizar la etapa ya construida con
suelo inicial de 10 GiB y plazo de 15 minutos; cada nueva revisión debe
identificar su manifiesto completo y repetir protocolo, firma y cierre.
