# HM-T5 — Habitación con color y luz de diagnóstico

2026-10-30. Build **`161090bc9fd5`**, instalado en SD para repetir la prueba visual
en consola. Sustituye la apariencia neutra de `de58ea2bb966`; conserva su
corrección de pausa/R. **El usuario confirma funcionamiento satisfactorio en
consola; la aceptación completa de HM-T5 sigue pendiente.**

## Problema y cambio

El usuario distinguía solamente a Heather. Las 31 formas estaban presentes,
pero 29 usaban el mismo RGB constante, sin iluminación que separase sus caras.
La referencia privada también mostraba un campo gris casi uniforme.

Las 29 formas neutras reciben ahora una paleta cíclica de seis colores y
sombreado plano por triángulo. La dirección unitaria de luz es
`(-0.48, 0.8, 0.36)`, con intensidad `0.32 + 0.68 * abs(N · L)`; las caras
degeneradas reciben `0.65`. El valor absoluto conserva el resultado al invertir
el orden de los vértices. Son colores de diagnóstico, sin significado de
colisión ni equivalencia con los materiales originales de la habitación.
HM-T4c.3 y la fidelidad de esos materiales siguen pendientes.

`room_diagnostic_colors` calcula únicamente RGB sobre la copia estática del
mapa ya validado. `RoomRenderer` lo aplica una vez, antes de publicar ese buffer
a la GPU. No añade buffers, texturas, asignaciones ni cálculo de luz por frame.
Se conservan posiciones, W, UV, cámara, recorrido, contactos, orden de dibujo,
los dos objetos de vidrio y las texturas de Heather. El HUD identifica
`29 FORMAS: COLOR/LUZ DIAGNOSTICO`.

## Validación local

Se conservó el fallo inicial con la función vacía en
`build/heather-room/diagnostic-v1/diagnostic-red.log`. La prueba comprueba colores
analíticos de caras horizontales/verticales, caras degeneradas, inversión de
orden, separación entre formas, idempotencia y ausencia de asignaciones.
El test del renderer comprueba su buffer estático real mediante el doble de
SDK y verifica que su hash permanece estable durante el replay de 100 pasos.

| Comprobación | Resultado |
| --- | --- |
| CTest seleccionadas, Release | 6/6 |
| CTest seleccionadas, ASan/UBSan | 6/6 |
| CTest seleccionadas, GCC fijado | 8/8 |
| Pruebas del empaquetado | 21/21 |
| Cobertura de siete componentes | Todas superan 80 % de líneas y ramas |
| Dominio de escena | 100 % líneas, 96.3 % ramas |
| Renderer | 99.3 % líneas, 95.2 % ramas |
| Compilación ARM | Aprobada; seis checksums verificados |

La auditoría privada A/B compara cuatro poses en Release y sanitizadores:
16 frames coloreados. Sus 27 804 vértices neutros cambian; los 96 de vidrio,
los frames dinámicos, cámara, rangos y geometría se conservan exactamente.
Un cálculo independiente con NumPy presenta error máximo de color
`5.177e-8`, inferior al límite `1e-6`.

Las cuatro vistas rasterizadas con los colores calculados por C++ conservan
exactamente los recuentos de píxeles visibles de Heather. Cambia el 100 % del
antiguo campo neutro y cada vista contiene entre 306 y 310 colores visibles
en esas superficies. La revisión visual permite separar suelo, paredes y
muebles. Esta referencia es software; la prueba ARM en emulador se registra
por separado abajo. Las imágenes y los datos originales permanecen fuera
del repositorio.

Presupuesto sin cambio: **38.33 MiB** de escena y **40.33/64 MiB** integrados.
Es contabilidad del presupuesto, no una medición de memoria física de consola.
Recibos locales:

- `reports/local/heather-room-diagnostic-appearance-v1.json`.
- `reports/local/heather-room-delivery-161090bc9fd5.json`.
- XML, logs y siete informes de cobertura en `build/heather-room/diagnostic-v1/`.

## Ejecutable ARM observado en Azahar

Azahar 2126.2, perfil aislado New 3DS, Vulkan y velocidad 100 %. Se verificó
en pantalla el ID `161090bc9fd5`, la etiqueta diagnóstica y `Error: none`.
Suelo, paredes y muebles aparecen con colores y caras distinguibles; Heather
conserva sus texturas. La cámara sigue fija.

| Acción | Lectura observada |
| --- | --- |
| A pausa, después L reinicia | PAUSED, Step 0, Clip 101, Q12 0, R raw/steps 0/0 |
| Espera sin botones de al menos 10 s | Mismos valores, Error none |
| R mantenido 2 s y liberado | PAUSED, Step 1, Q12 614, R raw/steps 1/1 |
| A, Arriba 1 s, Derecha 0.5 s y A | Heather cambia posición y orientación; PAUSED, Step 67, Q12 1736 |
| START | Retorno a la lista de aplicaciones; después cierre normal del emulador |

La apariencia permanece estable durante estas acciones. HUD de arranque:
`CPU: New fast`, `Load: 11472 ms`; una lectura muestra `FPS submit: 29.9` y
`Frame: 33.4 ms`. Son observaciones del emulador, no rendimiento de la consola.
Registro: `reports/local/heather-room-emulator-161090bc9fd5.json`.

## Paquete

Copias privadas A/B idénticas en
`heather-room-3ds-diagnostic-v1-copy-a` y
`heather-room-3ds-diagnostic-v1-copy-b`, bajo el directorio privado habitual.
Cada ZIP contiene 20 archivos de aplicación más `SHA256SUMS` (21 entradas),
con CRC y contenido releídos. Los recursos originales coinciden con los de
la entrega anterior. El paquete extraído pasa 12 replays de 100 pasos:
A/B × Release/sanitizadores × 25/60/143 Hz.

| Artefacto | Bytes | SHA-256 |
| --- | ---: | --- |
| `sd-card.zip` | 19909926 | `659d38ffa3dddb054808e71fe54bd1f354c35584a2b4997558a89c4a84477027` |
| `sh3_heather_room.3dsx` | 235236 | `400b9d20716ab37be4029c2defcdd14f8d96f0f81dcf6ea78caf34278d9c9d08` |
| `manifest.json` | 4241 | `908568a53df2f5fb049fe3e86a56f63d4d360ae4fc1fafafe18093c7f6a571c3` |

## Instalación SD verificada

La SD conectada coincidió con el UUID y los 20 archivos de la entrega
`de58ea2bb966`. Se instalaron los 20 archivos nuevos (19 904 839 bytes) en
`/3ds/sh3_heather_room/`, con staging, comparación de contenido y SHA-256
tras releerlos. El build anterior quedó respaldado y verificado en
`/sh3-room-install-161090bc9fd5-20261030T172513Z/previous-de58ea2bb966/`.
El visor anterior de 34 archivos permanece intacto. Se ejecutó sync y la
expulsión de `disk12` terminó correctamente; el volumen dejó de estar montado.

Recibo: `reports/local/heather-room-sd-delivery-161090bc9fd5.json`.
Instalador: `build/heather-room/sd-delivery-161090bc9fd5/install_sd.py`.
El chequeo final de formato C++, Ruff y repositorio pasó sin errores;
la guía empaquetada coincide con su fuente actual. La revisión del cambio
confirmó que el color se aplica después de validar el mapa y antes del flush,
sin modificar los recursos originales ni el buffer dinámico de Heather.

## Confirmación física comunicada

Tras instalar este build y solicitar la comprobación visual en consola, el
usuario respondió «funciona bien». Se registra como confirmación general
satisfactoria de esta entrega diagnóstica. No se aportan lecturas de HUD,
capturas ni resultados individuales de los pasos del protocolo, por lo que
no se atribuyen valores a Error, Load, FPS, Step, Q12 o contadores de R.

Registro: `reports/local/heather-room-physical-161090bc9fd5.json`.
Esta observación complementa la evidencia de Azahar y del build anterior;
no cierra por sí sola todos los criterios físicos de HM-T5.

## Comprobaciones restantes en consola

**Aplazadas por indicación del usuario el 2026-10-30.** Continúa
[HM-T4c.3.1](f06-01-heather-room-material-candidates.md), sin modificar
esta instalación ni descartar las observaciones físicas registradas.

Al abrirlo, confirmar el ID nuevo, `Error: none`, habitación y muebles
distinguibles y Heather texturada. Anotar CPU, Load, FPS submit y Frame.
Mover y girar, pausar, esperar 10 s, mantener R 2 s y reiniciar con L;
anotar Step, Clip, Q12, R presses y R steps. Seguir el
[protocolo HM-T5](../compatibility/heather-room.md) para el resto de casos.
Las observaciones físicas de `de58ea2bb966` siguen en su informe de pausa;
no se transfieren automáticamente al nuevo build. HOME+tapa combinados,
cadencia medida, recorrido/contactos y aceptación visual/física completa
siguen pendientes.
