# F02.07 / LP-C — Primer lote de productores VTLB

Fecha: 2026-10-18. Fuente: SRC66. Contrato:
[PW01–PW07](../../schemas/physical-write-probe-v1.md). Evidencia:
[metadatos públicos](../compatibility/physical-write-probe-evidence.json).

## Resultado y alcance

Se incorporaron ocho hooks en una copia privada nueva de PCSX2: cuatro puntos
de escritura sobre destinos host resueltos y cuatro invalidaciones conservadoras
para caché/handlers. Cubren las funciones VTLB de escritura escalar, 128 bits,
escritura directa de RAM y copia por bloques. La observación se efectúa antes
del acceso; un fallo invalida la evidencia sin impedir la escritura original.

**LG-I1 sigue parcial.** La aplicación PCSX2 completa no se enlazó ni ejecutó con
este parche. No hay comando PINE de armado ni conexión automática en la VM.
JIT, DMA, caché, restauración, época host y extremos de captura siguen pendientes;
JR mantiene su rechazo predeterminado y esta unidad no produce eventos `Read`.

## Componentes y SOLID

`PhysicalWrites` traduce un destino host efectivo a offset físico dentro del
bloque EE, sin desreferenciarlo. Reutiliza `LifetimeGuard` sin modificar su contrato
ni implementación. Rechaza anclas inválidas, overflow, intervalos vacíos y cruces
parciales del bloque; ignora intervalos completamente ajenos sin consumir eventos.
No convierte direcciones virtuales mediante máscaras: aliases ya resueltos al
mismo destino host se observan en el mismo offset.

`WriteBinding` tiene la única responsabilidad de conectar el puente y controlar
su duración mediante RAII. El registro admite una conexión; un intento anidado
no la sustituye. Un mutex protege callbacks y desconexión, y evita conservar el
puntero después de destruir la conexión. Guardia y puente deben sobrevivir a ella.
Los puntos de escritura no conocen planes de captura, sockets ni catálogo.

El mutex serializa los avisos, **no el efecto de memoria posterior**. Tampoco
acredita cobertura de callbacks omitidos. La serialización global, admisión de
modos y época no restaurable pertenecen a LG-I2; aún no se puede aceptar un sello
como prueba de continuidad real.

## Parche privado y compilación real

La copia parte del observador corregido de SRC51 en el commit fijado
`fd9d310ccbb6b8b62c976da8886a3c8fd3a10ff3`. Se modifican únicamente
`pcsx2/vtlb.cpp` y el listado CMake del proveedor; se agregan los cuatro archivos
propios de guardia/puente. Eliminar exactamente las inserciones en VTLB recupera
el archivo anterior completo. La evidencia identifica el diff y cada objeto.

Se compilaron cuatro unidades con las opciones reales generadas para PCSX2:
VTLB ON, VTLB OFF, guardia y puente. Apple Clang 21, x86_64, C++20, ThinLTO y SDK
explícito. El objeto ON referencia los dos callbacks; OFF no referencia ninguno.
Esto acredita compilación de las unidades, no enlace de la aplicación ni ejecución
del adaptador dentro de una VM. No se regeneró la configuración completa del proveedor.

La supervisión usó 180 segundos por compilación, 30 por ensayo, límite de etapa
de 1 GiB y suelo de 10 GiB. Todos los procesos finales cerraron sus grupos.
Se conservaron y reverificaron 2.934 archivos del baseline y 2.941 del observador
anterior; la copia derivada tiene 2.945. No se reemplazó ningún ejecutable existente.

## Ensayo de funciones del proveedor

Un harness privado incluye literalmente las cuatro funciones instrumentadas,
con hashes fijados. Usa RAM propia y dobles explícitos de mapa virtual, ciclo,
configuración, caché, handlers y almacenamiento de 128 bits. Los wrappers de
prueba registran el valor anterior al callback y después invocan el puente real.
No se sustituye el cuerpo de las funciones por una implementación propia.

**26 casos pasan en ON, OFF y ON con ASan/UBSan**: anchos 8/16/32/64/128,
alias al mismo destino, escritura igual, RAM ajena, dos fragmentos de página,
fallo después del primer fragmento, rechazo sin efecto y rutas de caché/handler.
Comprueban avisos antes del efecto, bytes finales y retornos originales. OFF
conserva los efectos sin avisos; caché/handler invalidan antes de su efecto.

Es una prueba de funciones con dependencias simuladas, no una sesión del emulador.
No acredita DMA, JIT, mapa real, rendimiento del juego ni comportamiento temporal
de hilos de PCSX2. Los cuerpos GPL y todo el harness compuesto permanecen privados;
los archivos nuevos del repositorio son propios.

## Pruebas host y regresión

- Siete escenarios CTest nuevos: traducción, fronteras, protección, cobertura
  desconocida, conexión, concurrencia y terminales. Incluyen 400 callbacks
  concurrentes y llamadas durante/después de desconectar y destruir el propietario.
- **67/67 CTest** pasan en Debug, Release y ASan/UBSan. La revisión de desconexión
  se incorporó antes de repetir las tres suites finales.
- Cobertura LLVM del puente: **37/37 líneas, 28/28 ramas y 38/38 regiones**;
  cabecera: 2/2 líneas, sin ramas. Gate local 80/80 aprobado.
- Regresión Python: **3.096/3.096**, sin errores, fallos ni omisiones;
  5.303/5.348 líneas y 1.449/1.482 ramas. Gate 80/80 aprobado.
- Ruff y formato: 137 archivos; controles de repositorio, custodia, enlaces y diff
  aprobados. La CI existente descubre los siete escenarios host y su cobertura.
  No se ejecutó CI remota ni el gate GCC local; LLVM no se presenta como GCC.

Los dos recibos de auditoría son idénticos: 7.523 bytes, SHA-256
`e3f89c9f22e3f100c378fb7e0869af7b828272d18dfdbb932a79a30edb0cf566`.
Se verifican fuentes, copias propias, objetos, logs, harness y ausencia de hooks
en OFF. Los recibos operativos se terminaron antes de la regresión completa.

Se conservaron tres intentos preparatorios rechazados: patrón ambiguo que también
aparecía en una lectura; muestreo del supervisor sin bytes asignados, rechazado
antes de lanzar el compilador; y variable de ciclo del doble sin uso en OFF bajo
`-Werror`. Se acotó el patrón, se completó la medición y se añadió una comprobación
del ciclo al fixture. No se rebajaron flags ni criterios; se repitió el harness
final en las tres modalidades.

SRC55–SRC64 permanecen intactos. Los cinco archivos de contrato/código/pruebas/
informe fijados por SRC65 también; su sexto insumo, CMake, se amplió intencionalmente
para registrar el nuevo target. Se conservó la versión exacta anterior y ambos
hashes se registran sin modificar la evidencia histórica. No hubo build 3DS;
el cambio de CMake altera la identidad de un build futuro.

## Cobertura restante y siguiente tarea

| Familia | Estado tras SRC66 |
|---|---|
| Escrituras mapeadas de las cuatro funciones VTLB | Hooks instalados en fuente privada, unidades compiladas y funciones probadas con dobles |
| Caché/handlers que pasan por esos hooks | Invalidación conservadora; no acreditan cobertura de todas sus escrituras |
| JIT/fastmem y accesos de caché por otras rutas | Pendiente |
| SPR, MFIFO, SIF, IPU y retorno desde GS | Pendiente |
| Modificaciones host, depurador, parches y arranque | Pendiente |
| Reset/restore/remapeo, época y escritores concurrentes | Pendiente |
| Armado, extremos, descubrimiento y transporte JR | Pendiente |

La matriz incluye 17 archivos pendientes fijados por hash; es un inventario de
brechas, no una prueba de exhaustividad. PW-T1–T4 están completadas; LG-I1–I4
permanecen abiertas.

La siguiente tarea es **LG-I1/DMA — escrituras directas que evitan VTLB**:

1. Localizar destinos efectivos y cantidades de SPR/MFIFO, SIF, IPU y retorno
   desde GS, incluidos desbordamientos de anillos y fragmentos. Entregable:
   matriz por función con dueño del hilo, sincronización y rango real escrito.
2. Añadir avisos previos usando el puente, sin cambiar bytes, orden ni retornos.
   Para efectos diferidos, mantener la captura no admisible hasta verificar el
   cierre de trabajos pendientes. Entregable: parche privado nuevo con hashes.
3. Ejecutar fixtures propios contra las funciones del proveedor: transferencia
   normal, wrap, longitud cero, error parcial, destino ajeno y escritura protegida
   que después recupera su valor. Aceptación: ninguna escritura protegida del lote
   puede completar un intervalo válido; efectos originales idénticos con ON/OFF.
4. Compilar unidades reales y repetir regresión. Conservar explícitas las brechas
   JIT/caché/host; no habilitar la VM hasta completar LG-I1–I4 y acreditar extremos.

Después siguen progreso temprano y captura LP-D: español/Normal/Normal, antes de
la carga y sin restaurar entre puntos; ≤48 estados, ≤256 solicitudes/hits,
60 segundos activos, 3.600 de pared, 8 GiB de etapa y 10 GiB libres. F02.07/Q05/G02,
procedencia real, semántica, dos salas y consola física continúan pendientes.
