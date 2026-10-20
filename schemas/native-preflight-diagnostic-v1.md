# PF — Diagnóstico local del preflight nativo

Estado: PF-T1–PF-T3 verificados en SRC118. Antecedente: SRC117 rechaza el inventario
de la VM pausada con `PlatformOriginFailure::preflight`, sin causa interna.

## Requisitos EARS

- **PF01:** WHEN una condición del preflight falla THEN la copia diagnóstica
  SHALL identificar rango/API, snapshot inicial, lectura/header, bit de caché
  fuera de rango o cambio del snapshot final, y conservar el rechazo original.
- **PF02:** WHEN se registra el fallo THEN el diagnóstico SHALL emitir una sola
  línea acotada por invocación, con metadatos del loader/header y sin bytes de
  juego, contenido de archivos, nombres de módulos ni nuevas capacidades.
- **PF03:** WHEN se prepara la copia THEN el procedimiento SHALL verificar el
  candidato y fuentes de SRC117, limitar los cambios a trazas del preflight y
  de los rechazos del registro de módulos, y preservar originales y cada
  iteración con sus hashes.
- **PF04:** WHEN se valida la copia THEN los controles existentes de origen
  nativo, incluido el bit de caché falsificado, SHALL conservar sus veredictos.
- **PF05:** WHEN se prueba la VM THEN el procedimiento SHALL usar un perfil
  nuevo, PINE de ruta corta, pausa inicial y cierre supervisado, sin jugar ni
  leer RAM de PS2; el resultado SHALL identificar el ejecutable exacto.
- **PF06:** IF la observación no identifica la condición interna THEN RT-T3a
  SHALL permanecer pendiente; identificar una condición SHALL NOT admitir
  inventario ni completar las muestras positivas o la matriz de escritores.
- **PF07:** IF falla la primera lectura del registro THEN la copia diagnóstica
  SHALL distinguir sus transiciones a fallo (revisión, capacidad, dirección
  nula, alta duplicada y retirada desconocida) sin omitir eventos ni recuperar
  automáticamente un registro invalidado.

## Diseño y pruebas

El primer fixture sustituye `preflight()` en una copia privada. La salida
local se ejecuta después de decidir el rechazo; no altera las interfaces,
la secuencia de lecturas, los límites ni el protocolo del servicio. El servicio
conserva la propiedad de IO y su cierre; esta instrumentación solo clasifica
una observación. No se incorpora a la biblioteca pública de producción.

La ampliación al registro emite como máximo una línea por transición a fallo.
Formatea enteros en una pila acotada y usa una escritura a stderr; no introduce
estructuras dinámicas ni cambia el ABI de `ImageLedger`. Se conserva la primera
iteración, que observa `first_read` dos veces, y se crea otra copia.

Se compilan los 20 escenarios existentes de `macos_platform_origin` en Debug,
Release y ASan/UBSan contra la copia. El caso `impostor` debe seguir rechazando
el bit falsificado antes del SPI y emitir `cache_flag_outside`. Después se
recompila ese único objeto con los flags reales y se enlaza un paquete nuevo.
Se comprueban firma, frameworks, testconfig, control sin VM y VM pausada.
La ampliación añade los 15 escenarios de identidad/registro y los 11 nativos
de imagen, incluidos eventos concurrentes y fork, en los mismos tres modos.

- [x] **PF-T1:** fixtures acotados, copias reversibles y 198 ejecuciones de regresión.
- [x] **PF-T2:** candidatos diagnósticos firmados y arranques supervisados.
- [x] **PF-T3 / RT-T3a:** causa observada, evidencia publicable y siguiente
  corrección definida sin relajar el criterio de inventario.

El registro alcanza 1.024 entradas y rechaza un intento de alta con revisión
1.025. La comprobación de capacidad precede a la de duplicados: esta evidencia
no cuenta el total de módulos ni prueba por sí sola que el intento adicional
corresponda a una dirección nueva. La siguiente etapa debe medirlo antes de
proponer otra capacidad y verificar su coste de memoria/plazo.
El control sin VM también registra capacidad agotada después de cerrar el
servicio; el censo posterior debe abarcar ambos tipos de arranque.
