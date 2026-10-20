# Lifecycle probe v1 — LC01–LC08

Integración acotada de LG-I2. El objetivo es invalidar antes de cambios de vida
de la VM, incluso cuando terminan en error o restauran los mismos bytes.

## Requisitos EARS

- **LC01:** WHEN comienza una transición cubierta de reset, restauración,
  remapeo, configuración o cierre THEN el productor SHALL avanzar la época host
  e invalidar la guardia conectada antes del primer efecto destructivo cubierto.
- **LC02:** WHILE el proceso host siga vivo THEN la época SHALL crecer sin
  restaurarse con la VM, desconectar el puente ni retroceder el ciclo emulado.
  IF se agota el contador THEN SHALL quedar permanentemente no disponible (cero),
  sin reutilizar épocas. Un nuevo proceso requiere también una nueva sesión.
- **LC03:** WHEN se entrega un cambio al puente THEN SHALL usar el mismo bloqueo
  de las notificaciones de escritura, conservar la primera causa terminal y
  rechazar conservadoramente tipos de evento ajenos al ciclo de vida.
- **LC04:** WHEN el cargador supera las comprobaciones previas y comienza la
  preparación de restauración THEN SHALL invalidar antes de esperar trabajos,
  cambiar protecciones o sobrescribir estructuras. IF falla después THEN SHALL
  mantener inválido el intervalo aunque se ejecute un reset de recuperación.
- **LC05:** WHEN reset se difiere por ejecución activa THEN SHALL invalidar antes
  de cambiar a Resetting; IF un reset pausado se cancela antes de efectos THEN
  SHALL conservar la observación. Una configuración reaplicada puede invalidar
  conservadoramente aunque sus valores finales sean iguales.
- **LC06:** WHEN una transición incluye varias fronteras instrumentadas THEN
  SHALL permitir varios avances sin reconstruir una identidad anterior; SHALL
  conservar efectos, errores y retornos del proveedor tanto en ON como en OFF.
- **LC07:** WHEN se valida el lote THEN SHALL distinguir pruebas del núcleo,
  funciones privadas exactas con dobles, unidades compiladas y ejecución de VM;
  SHALL conservar snapshots de versiones anteriores al evolucionar el puente.
- **LC08:** WHILE no se demuestre exclusión de escritores/CPU/trabajos, admisión
  por modo y unión de extremos THEN SHALL mantener cerrado el armado real.
  Leer la época o superar estos tests SHALL NOT acreditar continuidad.

## Diseño y SOLID

`HostEpoch` solo administra un contador atómico de 64 bits: comienza en uno,
avanza y queda en cero al agotar su espacio. No ofrece reset, copia ni movimiento.
La instancia del puente pertenece al proceso nativo y no forma parte de ninguna
estructura de save state. La semántica relajada del contador proporciona identidad;
no publica memoria de la VM ni sustituye un protocolo de exclusión.

`PhysicalWrites` reutiliza el bloqueo de conexión/avisos y traduce causas de
ciclo de vida al núcleo `LifetimeGuard`, que permanece sin cambios. El avance
ocurre incluso sin conexión; no se omiten transiciones entre intervalos. La época
no identifica un snapshot ni habilita armar a través de PINE.

Los avisos se sitúan en entradas y fronteras del proveedor. Los callbacks anidados
pueden avanzar más de una vez: no se promete una época por operación de alto nivel.
Se conservan controles previos sin efecto y la lógica del proveedor. La futura
admisión deberá verificar época inicial/final dentro de una sección que excluya
los efectos concurrentes, incluidos PINE, GS y escritores opcionales.

## Tareas acotadas

1. **LC-T1 / LC01,04–08:** fijar inventario, orden y alcance de reset, carga,
   remapeo, cambio de CPU/configuración, ancla y cierre. Distinguir rechazos previos,
   efectos parciales y entradas sin cobertura exhaustiva.
2. **LC-T2 / LC01–06:** implementar contador y puente tipado; nueva copia privada
   con avisos previos y fuentes propias actualizadas. Conservar snapshots y hashes
   del puente anterior, sin modificar evidencias históricas.
3. **LC-T3 / LC02–07:** probar saturación, concurrencia del contador/avisos,
   conexión ausente, terminales y retroceso del ciclo; ejecutar funciones reales
   seleccionadas con mapas/ZIP/trabajos propios, fallos parciales y memoria igual.
4. **LC-T4 / LC07,08:** comparar ON/OFF/anterior, sanitizadores, unidades reales,
   regresión y cobertura nueva del núcleo/puente; dos auditorías iguales. Dejar
   explícitas funciones solo compiladas y pendientes de admisión, extremos y VM.
