# F02.07 / LP-C — Vinculación runtime revocable (SRC112)

## Resultado y alcance

Completa **RB-T1 / DW-T3a** de [RB01–RB08](../../schemas/runtime-diagnostic-binding-v1.md):
el diagnóstico conserva un alcance inmutable, revocable y con plazo propio.
DW consulta ese alcance durante preparación, muestreo, entrega y espera ociosa.
**DW-T3 completo, RB-T2/RB-T3 y captura permanecen pendientes.**

Se ejecutan hilos DW y núcleos reales de CPU, exclusión cooperativa, drenaje PINE,
retención y controles VU/GS. Los snapshots de épocas/hechos y el inventario son
locales de prueba. No se ejecuta PCSX2 ni una VM; esta evidencia no acredita
que un proveedor real haya adquirido las guardias que declara.

## Implementación

`DiagnosticValidity` separa la consulta de validez del presupuesto y del trabajo
nativo. Su implementación no puede hacer IO, bloquear, reentrar al trabajador
ni adquirir locks compartidos con CPU. `RuntimeDiagnosticBinding` tiene un dueño
para activar/revalidar y permite revocación atómica desde cualquier hilo.
El snapshot se publica una vez y nunca se modifica. Cambiar un dato y volver al
valor anterior, reactivar o usar otro dueño invalida la instancia.

La activación exige ID propio, cuatro épocas no nulas ni máximas y deadline
futuro de hasta cinco segundos. Las seis condiciones estructurales son CPU,
frontera, pausa y retención PINE/VU/GS. Los otros doce hechos mantienen sus
valores desconocidos, violados o satisfechos; enums inválidos se normalizan a
desconocido. Este filtrado no concede permiso de captura. La unicidad global de
IDs entre instancias deberá garantizarla el coordinador.

La fábrica decoradora es privada. La función de composición usa la misma
vinculación para añadir datos y para validar DW, evitando alcances distintos.
El decorador se reserva antes de permitir que el hijo adquiera recursos.
Creación, preparación, muestreo, cierre y destrucción del trabajo permanecen
en el trabajador. El hijo debe aportar inventario sin épocas ni hechos runtime;
se rechaza la composición si ya los contiene. El modo DW anterior, sin este
validador opcional, conserva su comportamiento.

La separación sigue SOLID: el alcance decide validez, DW administra trabajo y
presupuesto, el decorador compone datos y el dueño del canal entrega bytes.
Los puertos permiten sustituir reloj, trabajo y validador sin introducir
dependencias de VMManager en el núcleo ni ampliar el contrato del inventario.

El plazo del alcance no se reinicia con cada solicitud. Las esperas internas
consultan la validez cada 20 ms nominales, incluso entre entregas, sin exigir
polling del dueño. No se promete latencia del SO ni interrupción de un hijo
bloqueado: la revocación impide aceptar su resultado cuando retorna, pero su
limpieza puede seguir pendiente. Revocar no une hilos ni cierra recursos.
La prueba conjunta revoca antes de liberar GS, VU y PINE, y une DW después.

## Validación

- **428 escenarios por variante**, en Debug, Release, AddressSanitizer/UBSan y
  cobertura x86_64: **1712 ejecuciones finales**. Incluyen los 402 anteriores y
  26 nuevos. El escenario previo largo de reloj real queda compilado y excluido
  de estas ejecuciones; el nuevo vencimiento autónomo usa reloj real de 200 ms.
- **67 ejecuciones con ThreadSanitizer arm64**, sin diagnósticos de carreras:
  24 de DW, 17 de entrega y 26 de vinculación runtime.
- **Ocho controles negativos finales detectados**: omitir validez, comparar
  épocas o deadline, borrar épocas, omitir cierre, aceptar runtime del hijo y
  eliminar polling durante entrega o espera ociosa.
- Cobertura agregada registrada: núcleo runtime **97/97 líneas, 100 %** y
  **101/108 ramas, 93,52 %**; DW **239/241 líneas, 99,17 %**. LLVM conserva el
  aviso agregado de 28 funciones con datos incompatibles. Se publican métricas
  por fuente; no se atribuye cobertura al coordinador ni se afirma cobertura
  global completa. ASan usa `detect_leaks=0`; no acredita ausencia de fugas.
- **58 controles de repositorio y supervisión**; auditoría repetida con salida
  idéntica, custodia por hashes y publicación de metadata.

Los escenarios cubren cada condición estructural y los estados de los doce
hechos restantes; cada época/ID inválido; reloj regresivo y fronteras exactas;
cambio/regreso; cancelación durante fábrica, preparación, muestreo y entrega;
17 bytes parciales y 294 bytes escritos sin confirmación tardía; cierre pendiente
y fallido; vida compartida; 100 carreras cancelación/confirmación y 100 carreras
activación/lectura. La prueba de espera autónoma observa consultas del trabajador
sin invocar status, presupuesto o entrega después de revocar.

## Intentos conservados y custodia

Se conservan las etapas anteriores: 1708 ejecuciones de la versión inicial,
1712 de la versión con polling y 67 comprobaciones TSan previas. El primer
selector de mutación coincidía con dos fragmentos y abortó antes de escribir o
ejecutar comandos. Después, siete mutaciones fueron detectadas y la que quitaba
polling ocioso escapó: la prueba revocaba demasiado pronto, antes de asegurar
la espera. Se conserva esa salida 0. Se corrigió únicamente la prueba para
observar comprobaciones repetidas del trabajador y se repitieron las cuatro
variantes, TSan y los ocho controles en etapas nuevas.

Otro intento de preparación conservaba la ruta de la etapa anterior SRC110;
`exist_ok=False` impidió sobrescribirla antes de ejecutar comandos. La auditoría
contrasta todos sus archivos y confirma que permanece intacta. Se preservan
ambos errores preparatorios, sin presentarlos como validaciones satisfactorias.

Los 137 inputs de SRC111 se congelan antes de modificar cuatro entradas:
DW, su cabecera, CMake nativo y el apéndice de estado del contrato DW. Se reutilizan
12 fuentes/cabeceras de coordinador contrastadas con sus evidencias anteriores.
Tres fuentes privadas de VMManager/PINE se contrastan para planificar RB-T2,
sin editarlas. La evidencia actual vincula 154 inputs públicos y las fuentes,
binarios, perfiles, logs y recibos de cada etapa privada. Los comandos supervisados
respetan reserva/suelo de 10 GiB y máximo de 512 MiB por etapa.

CMake incorpora las pruebas al pipeline nativo ya existente de macOS/Linux,
con y sin sanitizadores. Esta ejecución es local en macOS: no acredita CI remoto,
Linux ni compilación 3DS. No usa ISO/BIOS, no modifica el candidato PCSX2 instalado
y no produce ReadEvents ni capacidades de captura.

## Siguiente tarea

**RB-T2 / DW-T3b:** el proveedor privado hoy completa/retira el drenaje al observar
`held` en `PollObserverPineDrain`. Debe conservarlo durante el intento diagnóstico,
muestrear las épocas y los hechos bajo las guardias, y revocar antes de cada
retiro o transición de VM. Los hooks deberán cubrir cambios entre lecturas;
comparar generaciones dos veces no basta. Verificar cuerpos ON/OFF y luego
**RB-T3** con candidato enlazado y VM, sin promover hechos no acreditados.
