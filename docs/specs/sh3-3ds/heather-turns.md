# HG — Animaciones originales de giro de Heather

Instancia preparatoria **F06.02/heather-turns**, 2026-10-30. Se continúa
después de la confirmación funcional de `c3aae59d1a70`. Por petición expresa
del usuario se aplazan las mediciones y pruebas adicionales de HM-T5.
La navegación de pared 60 continúa pospuesta. No se cierran G04/G05/F06.

## Objetivo y dependencias

Incorporar en una futura entrega los clips originales de giro sobre el sitio,
con transiciones contrastadas y traslación mundial aplicada una sola vez.
HL ya cubre espera/caminar/correr; HM aporta intención, contactos y escena.
HG-T1–3 verifican fuentes/poses y fijan el contrato; HG-T4 completa el núcleo,
SRI2, controles/contactos de escena, presupuesto y compilación ARM.
HG-T5 prepara los paquetes A/B y el protocolo de la nueva entrega;
la copia a SD está verificada y el usuario confirmó la prueba funcional
acotada de HG, con sus lecturas y límites registrados.
Las dependencias generales de F06.02 continúan abiertas: se adelanta este
perfil de inspección, sin integrar campaña ni afirmar movimiento PS2 general.

Entradas autorizadas: MDL522/ANM525 extraídos y su relectura desde ISO, tabla del ELF
europeo y estados conservados de HM-T2b.3/.6. HG-T2 añade una sesión privada de
PCSX2 desde un estado de espera autenticado, con controles por el puerto normal
y capturas en cada retorno. Las sesiones y sus restauraciones permanecen
separadas. No hay escrituras directas a memoria del juego.

## Requisitos EARS

- **HG01:** CUANDO inventaría un clip DEBERÁ cotejar extracción/ISO y sus hashes,
  descriptor ELF y su conversión PAL frente a RAM, rango y huesos activos.
  No DEBERÁ deducir una transición del descriptor o de la dirección del mando.
- **HG02:** CUANDO compara una pose estable DEBERÁ exigir retorno completo,
  dos canales coherentes, origen igual al destino, modo 1, mezcla y offset de velocidad cero
  y avance igual a velocidad PAL por ticks. DEBERÁ distinguir contador
  devuelto de fase evaluada y envolver ambos índices dentro del mismo clip.
- **HG03:** CUANDO reconstruye una pose DEBERÁ usar ANM original, NLERP corto,
  traslaciones locales y composición jerárquica; cotejar las 36 matrices modelo
  frente a RAM con límite absoluto 0,001. Contador posterior, clip contrario
  y wrap incorrecto DEBERÁN servir como controles negativos discriminantes.
- **HG04:** SI observa una mezcla sin su origen congelado y secuencia previa
  DEBERÁ registrarla como incompleta, sin acreditar sus poses ni transiciones.
  Muestras separadas no DEBERÁN contarse como un ciclo continuo completo.
- **HG05:** CUANDO publica evidencia DEBERÁ conservar hashes, sesiones,
  alcance y resultados negativos, sin recursos privados en git/CI. Código
  nuevo DEBERÁ tener pruebas sintéticas y cobertura individual ≥80/80.
- **HG06:** CUANDO amplía el perfil nativo DEBERÁ aplicar
  [HGT01–12](../../../schemas/heather-turns-native-v1.md): separar arcos
  observados de política de controles, conservar perfil 1/SRI1, fijar
  vectores previos al código y medir memoria/atomicidad al integrarlo.

## Diseño de HG-T1

`tools/qa/steady_clip_observation.py` valida dos registros de canal delimitados
y calcula la fase previa mediante el oráculo de reloj existente. No lee
archivos, conoce direcciones EE ni modifica el runtime. El adaptador privado
`build/heather-turns/audit_existing.py` autentica entradas, extrae registros,
reconstruye poses mediante los oráculos existentes y publica solo metadatos.
Tests propios: `tests/python/test_steady_clip_observation.py`.
Evidencia: `reports/local/heather-turns-existing-v1.json` y repetición `-O`.
Informe público previsto: `docs/execution/f06-02-heather-turns-inventory.md`.

## Diseño y resultado de HG-T2

Captura privada `heather-turns-capture-v4`: ancla restaurada una vez,
70 actualizaciones únicas consecutivas y un duplicado del ancla excluido.
Los intentos v1–v3 se conservan aparte; no aportan ciclos completos.
La copia de PCSX2 usa un identificador de aplicación exclusivo, con ejecutable
idéntico al original. Dos controles sostenidos del propio emulador, sin turbo,
alimentan derecha/izquierda por el puerto de mando. Se eliminan solamente
las asignaciones directas Left/Right del perfil privado para que la pérdida
de foco no anule esos controles. Se verifican los bits y sus flancos en RAM.

`tools/qa/steady_cycle_observation.py` exige continuidad de ordinal/ciclo,
identidad de clip y avance de fase, y al menos un período completo. El adaptador
local `build/heather-turns/audit_cycles.py` autentica estados/recibos, recursos,
código y restauración, reconstruye las poses y valida las cuatro mezclas.
Usa los oráculos independientes existentes; no ejecuta el núcleo de consola.
19 pruebas sintéticas nuevas y gate individual 100/100, añadida a CI.

[HG-T2: evidencia completa](../../execution/f06-02-heather-turns-cycles.md).
La mezcla congela la pose local interpolada anterior; el índice entero de
origen por sí solo no basta. El offset de mezcla puede persistir inactivo
en modo 1: no es un offset de velocidad ni altera su fase.

## Diseño y resultado de HG-T3

[Contrato nativo v1](../../../schemas/heather-turns-native-v1.md), estado
`specified_not_integrated`: perfil 2, cinco clips, 78 muestras. Añade 107/108
al final de SRI2, preservando los índices y los cinco arcos de HL. Los cuatro
arcos nuevos fijan caché local interpolada, entrada 768/768 y salida 1024/410.
No habilita interrupciones ni arcos directos entre giros. La aplicación
conservará la última acción completa y encadenará arcos permitidos mediante
espera; el yaw actual sigue siendo independiente de la animación retenida.

La capacidad física se amplía en HG-T4.2 de 64 a 80 muestras sin ampliar el límite
de SRI1 (64) ni las cantidades exactas de cada perfil SRI2 (58/78). Se fijan
310356 bytes de archivo y +32704 bytes por rig decodificado; el pico real
de memoria y la atomicidad C++ se verificarán en HG-T4.

[Vectores sintéticos](../../../tests/fixtures/synthetic/heather-turns-native-v1.json)
y [comprobaciones independientes](../../../tests/python/test_heather_turns_contract.py):
248 pruebas del contrato; 492 relacionadas en total. Ninguna lee recursos
privados ni ejecuta la futura implementación de giros. Incluyen matriz de
25 selecciones, 32 combinaciones de botones, 25 rutas, 36 pasos de replay,
76 rechazos y las obligaciones de fallo/publicación/ciclo de vida.
[Informe HG-T3](../../execution/f06-02-heather-turns-contract.md).

## Resultado de HG-T4.1

[Núcleo de giros implementado y validado](../../execution/f06-02-heather-turns-core.md):
perfil 2 de cinco clips, tasas por arco, caché interpolada y propagación de
identidad al inicializar/reiniciar. Los consumidores legado usan cantidad
activa tres; la ampliación del transporte se completa en HG-T4.2.

405 resultados contra los vectores originales; 1402 rechazos atómicos y
1303 pasos correctos/reintentos. Los 16 casos CTest relacionados pasan en
Clang, ASan/UBSan y GCC; 745 pruebas Python y seis gates individuales ≥80/80.
Reloj/publicación 100/100; poses 98,4/89,5. Estado+workspace 18040/32768 bytes,
sin asignaciones C++ por actualización. No implica cotejo privado del nuevo
SRI2, controles del perfil 2, compilación ARM ni nueva aceptación de consola.

## Resultado de HG-T4.2

[Transporte y recursos verificados](../../execution/f06-02-heather-turns-sri2.md):
SRI2 acepta exclusivamente ID 1/3 clips/58 muestras e ID 2/5 clips/78 muestras.
Capacidad física 80, aceptación SRI1 limitada a 64. Productor/lector/oráculo
coinciden y los paquetes privados A/B son idénticos: SRI de 310356 bytes,
modelo decodificado host de 422412 bytes, incremento 32704 por rig.

70 retornos nativos/2520 matrices frente a HG-T2, máximo 0,00048828125
contra 0,001; extremos crudos 5,96046448e-8 contra 1e-7. Se conservan los
58 TR previos y toda la geometría/materiales/texturas compartidos. El lector
supera 5745 rechazos atómicos; 834 pruebas Python y 25 CTest en Clang,
ASan/UBSan y GCC 12. Seis gates C++ ≥80/80 y seis Python 100/100.
Al cierre de HG-T4.2 quedaban acciones/controles HM, pico final de memoria,
ARM y entrega física; la coordinación se resuelve en la unidad siguiente.

## Resultado de HG-T4.3

[Cinco acciones integradas con HM](../../execution/f06-02-heather-turns-integration.md):
selección tipada, objetivo completo reemplazable, puentes por espera y yaw
actual independiente del clip retenido. Se conserva la ruta del perfil 1.
El actor publica junto con contactos; 156 fallos y 156 reintentos conservan
instantánea byte a byte, orden de callbacks y rechazo de reentradas.

32 combinaciones de botones, 25 rutas y 36 filas de replay ejecutadas contra
los literales HG-T3. Seis fases de giro verifican pausa/R/reinicio/HOME/tapa
con el adaptador real y dobles SDK; SRI2 perfil 2 pasa por controles, contactos
y render a 25/60/143 Hz. 27 CTest en Clang/ASan/GCC, 633 pruebas Python,
16 gates individuales ≥80/80. Actor 27960/controlador 28024/bucle 28072 bytes
host y guardias de asignaciones superadas. El pico/pila final y ARM quedan
en HG-T4.4; al cierre de HG-T4.3 no había un nuevo build ni aceptación física.

## Resultado de HG-T4.4

[Recursos y ARM verificados](../../execution/f06-02-heather-turns-resources.md):
inventarios ABI host/ARM, presupuesto conservador 51824452 bytes (49,42 MiB)
sobre 64 MiB, con más del 20 % libre. Las copias privadas A/B, ejecutadas en
Release y ASan/UBSan, dan el mismo pico de buffers rastreados de 34252665 bytes;
2048 actualizaciones en total sin asignaciones por paso y liberación completa.
No son medidas de RSS ni del pico físico de la consola.

Inventario de pila de 24 unidades, recursión de ordenación acotada y reserva
externa de 8 KiB: 32048 bytes Clang, 29120 GCC y 28016 ARM, frente a 32768.
La reserva externa no demuestra el peor caso interno del SDK; medición física
pendiente. 30 CTest Release Clang/GCC, 28 ASan/UBSan y 28 con cobertura;
17 gates individuales ≥80/80 y ocho pruebas del auditor de pila.
Repetido el cotejo privado de 70 poses/2520 matrices, máximo 0,00048828125.
ARM `0188790baedd` compilado y seis archivos verificados por SHA-256.
HG-T4 queda completa en este alcance local. En esa etapa quedaba HG-T5;
no se copió a SD ni se acreditó ejecución ARM. HM-T5 adicional y pared 60
siguen aplazadas.

## Resultado de HG-T5

[Entrega identificada preparada](../../execution/f06-02-heather-turns-delivery.md):
build exacto `0188790baedd`, paquetes privados A/B idénticos, 29 archivos de SD
y ZIP de 30 entradas con hashes. Runtime de cinco clips/78 muestras idéntico
al auditado en HG-T4.4; materiales/contactos conservados y presupuesto 49,42 MiB.
22 pruebas de empaquetado y ocho ejecuciones host desde las copias extraídas
superadas. El [protocolo](../../compatibility/heather-turns.md) tiene 123 pasos
y 69 puntos numéricos cotejados por configuración Release/ASan, sin ejecución
física. HG-T5 completa la preparación y la copia posterior a SD: 29 archivos
releídos, respaldo de `c3aae59d1a70` y expulsión segura.
[Prueba funcional de consola aceptada según el usuario](../../compatibility/heather-turns-results.md):
ambos ciclos/retornos, inversiones, cancelación, pausa/R, HOME/tapa, L,
RUNNING y START; R steps acumulado 129. Se preservan lecturas R raw distintas
y la ausencia de una traza completa por pulsación; sin medidas físicas nuevas
de rendimiento/memoria.
HM-T5 adicional y pared 60 siguen aplazadas; F06.02/G04/G05 permanecen abiertos.

## Secuencia

- [x] **HG-T1 — Fuentes y poses existentes.** Cotejar descriptores y muestras
  de derecha/izquierda, poses estables y controles negativos. Delimitar huecos
  de adquisición. HG01–05; RF04.03/RF04.04, preparación de T04.
  [Evidencia](../../execution/f06-02-heather-turns-inventory.md): extracción/ISO
  idénticas, 20 muestras de giro, cinco poses/180 matrices, máximo 0,000343
  frente a 0,001 y 12 controles negativos. 195 pruebas relacionadas, 72 nuevas,
  cobertura 100/100; informe normal/`-O` idéntico. Un estado de mezcla se
  conserva como incompleto. No cambia SRI2 ni el build de consola.
- [x] **HG-T2 — Ciclos y transiciones observadas.** Capturar por controles
  normales ciclos completos y espera↔giro en ambos sentidos; conservar
  origen interpolado/congelado, wrap y restauraciones. No extrapolar el
  giro en marcha, que en las muestras existentes usa caminar 109.
  Completada: dos ciclos de 19 poses, cuatro transiciones y 2520 matrices;
  máximo 0,000468465 < 0,001. 162 controles negativos rechazados y dos
  coincidencias de pose final documentadas. 214 pruebas relacionadas,
  cobertura nueva 100/100 y auditoría normal/`-O` idéntica.
- [x] **HG-T3 — Contrato y vectores nativos.** Estados, nueve arcos, prioridad,
  errores, rutas, publicación, límites y formato fijados en HGT01–12.
  Vectores y oráculos de consistencia anteriores a la implementación;
  se conserva `specified_not_integrated` y la entrega de consola existente.
- [x] **HG-T4 — Integración acotada.** Núcleo y publicación atómica con HM,
  replays, errores, presupuesto, gates y ARM según el contrato verificado.
  - [x] **HG-T4.1:** perfil y reloj/evaluador de cinco clips; tasas por arco,
    cuatro arcos con caché, continuidad y errores. Consumir los
    literales HG y conservar HL. HGT01–04/09/12. Núcleo y seis gates validados;
    evidencia en el informe anterior, sin ampliar aún el transporte ni la escena.
  - [x] **HG-T4.2:** separar límites SRI1/capacidad/perfil; productor y lector
    SRI2 ID 2, pruebas de corrupción/atomicidad y preparación A/B de las 78
    muestras. Verificar los 70 retornos originales sin ampliar tolerancias.
    HGT01/08/09/11/12. A/B idénticos y 70 retornos validados; evidencia en
    el informe de transporte, pendiente coordinación de escena y ARM.
  - [x] **HG-T4.3:** acción de cinco estados en actor/controlador/bucle;
    puentes y reemplazo de intención, contactos, pausa/R/reset/HOME/tapa,
    replays y fallos de ambos canales. HGT05–07/10/12. Vectores, 156 fallos
    atómicos/reintentos, runtime perfil 2 y ciclo de vida verificados en host;
    evidencia y límites en el informe de integración.
  - [x] **HG-T4.4:** medir almacenamiento/pico/pila host y ARM, cero asignaciones
    por paso, gates individuales ≥80/80, regresiones HL/HM y compilación ARM.
    Registrar resultados antes de empaquetar. HGT07–12. Inventarios ABI y pila
    de compilador con reserva, pico de buffers en host y presupuesto 49,42/64 MiB;
    17 gates y ARM `0188790baedd` verificados. Límites en el informe de recursos.
- [x] **HG-T5 — Entrega identificada.** Paquete A/B y protocolo de consola.
  Build `0188790baedd`, 29 archivos de instalación verificados, ZIP idénticos
  y protocolo numérico cotejado en host. Copia a SD verificada, respaldo anterior
  conservado y tarjeta expulsada. Prueba funcional acotada aceptada según el
  usuario; evidencia y límites en el informe físico, sin cerrar HM-T5 completo.
  Las mediciones/pruebas adicionales de HM-T5 se mantienen aplazadas.
