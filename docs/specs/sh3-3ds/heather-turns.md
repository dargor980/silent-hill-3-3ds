# HG — Animaciones originales de giro de Heather

Instancia preparatoria **F06.02/heather-turns**, 2026-10-30. Se continúa
después de la confirmación funcional de `c3aae59d1a70`. Por petición expresa
del usuario se aplazan las mediciones y pruebas adicionales de HM-T5.
La navegación de pared 60 continúa pospuesta. No se cierran G04/G05/F06.

## Objetivo y dependencias

Incorporar en una futura entrega los clips originales de giro sobre el sitio,
con transiciones contrastadas y traslación mundial aplicada una sola vez.
HL ya cubre espera/caminar/correr; HM aporta intención, contactos y escena.
Esta unidad verifica las fuentes y poses existentes antes de ampliar HLC/SRI2.
Las dependencias generales de F06.02 continúan abiertas: se adelanta solo
investigación de fuentes, sin integrar campaña ni afirmar movimiento PS2 general.

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
- [ ] **HG-T3 — Contrato y vectores nativos.** Fijar estados, arcos, prioridad
  y formato compatible antes de cambiar núcleo, productor o lector.
- [ ] **HG-T4 — Integración acotada.** Núcleo y publicación atómica con HM,
  replays, errores, presupuesto, gates y ARM según el contrato verificado.
- [ ] **HG-T5 — Entrega identificada.** Paquete A/B y protocolo de consola.
  Las mediciones/pruebas adicionales de HM-T5 se mantienen aplazadas.
