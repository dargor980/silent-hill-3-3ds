# F02.07 — Objeto del driver, despacho y posición

Fecha: 2026-10-18. Unidad SRC59 de `camera-resource-link-eu/origin/load-provenance/LP-C`.
Continúa [SRC58](f02-07-catalog-open.md). Contrato [DT01–DT09](../../schemas/driver-transfer-v1.md)
y [evidencia](../compatibility/driver-transfer-evidence.json).

## Resultado y alcance

Se implementaron dos validadores puros para el pool del driver y una pareja de
pausas de despacho. Comprueban handle/generación, objeto, tabla de funciones,
argumentos, posición, cantidad devuelta y hash final. El subconjunto soporta
una transferencia positiva con buffer y dentro de un sector de 2048 bytes.

La investigación fija el perfil al ELF/estado europeo y verifica nuevamente
ISO, contenedor y payload. **No hubo nueva sesión de PCSX2 ni captura de carga.**
El adaptador valida evidencia suministrada; no acredita identidad de archivo,
apertura real, ruta interior, origen de caché ni lectura de disco. LP-C sigue
parcial y no se producen eventos `Read`, vínculos o capacidades.

## Investigación estática

**14 ventanas y 3.852 bytes** coinciden entre ELF y estado: inicialización,
asignación, revalidación y liberación de objeto, búsqueda por handle, apertura,
seek y su despacho, lector con buffer, ruta de sector único, despacho de lectura
y envoltorios backend. Diecinueve instrucciones fijan las decisiones revisadas;
la tabla de funciones de 24 bytes también coincide. Direcciones y palabras
originales se conservan solo en el plan privado.

El pool tiene cabecera de 24 bytes y filas de 48 bytes. Se observan capacidad
16 y desplazamiento de índice 1: no se deriva este último de la capacidad ni
se afirma que todos los índices sean direccionables. La búsqueda aplica la
máscara observada y compara el handle completo. La asignación usa el contador
anterior para formar el handle y guarda el contador incrementado. Esto difiere
de la generación del descriptor de archivo de SRC57. El contrato admite solo
el subconjunto sin desbordamiento y exige que el índice pertenezca al pool.

Se contrasta SLLV con `R5900OpcodeImpl.cpp` de la revisión PCSX2 ya fijada en
SRC57. Las copias baseline/instrumentada siguen iguales: 41.762 bytes y SHA-256
`6ae749a7e3a297a291f1844d2f96a17bf7c53a9c6f6f4ab4ddab27781a78c2b4`.
No se copia implementación externa al proyecto.

Los **16 objetos están cerrados** en el estado posterior: una fila conserva
tabla de funciones residual y las otras 15 tienen ese campo nulo. El primer
ensayo operativo supuso erróneamente una tabla común en todas las filas y fue
rechazado antes de crear el plan o publicar informes; un segundo intento
encontró el mismo rechazo. La corrección registra los valores observados,
sin convertir filas residuales en objetos activos.

La posición está en bytes. El lector acota el resultado al tamaño del archivo
y añade los bytes devueltos a la posición. La ruta de sector único compara
un índice de caché y puede copiar desde el buffer sin solicitar otra lectura
al backend. La referencia backend sigue siendo opaca: su presencia o el
tamaño coincidente no prueban qué archivo o sector representa.

Dos ejecuciones corregidas generan informes idénticos de **4.426 bytes**, SHA-256
`ae50f33cd7f944cee55114f00c05b9f6520d5834d646f5549a7831eccc558f10`.
Lectores cerrados antes de publicación; estado, catálogo, evidencia, plan previo
y fuentes PCSX2 revalidados. Plan nuevo sin sobrescritura, directorio 0700 y
archivo 0600. El handle provisional usado para validar la forma del perfil no
se presenta como handle activo ni se reutiliza para la futura captura.

## Diseño y pruebas

[driver_object](../../tools/inspectors/driver_object.py) recibe cuatro rangos LF
y produce una vista privada inmutable. [driver_transfer](../../tools/inspectors/driver_transfer.py)
compara dos pausas de ocho rangos: raíz, pool, objeto, tabla de funciones,
despacho, lector, destino y argumentos guardados. Adquisición/custodia y origen
ISO siguen separados. No cambia PCSX2 ni el runtime de Nintendo.

La pareja exige identidad y mapas estables, slots distintos, secuencias
consecutivas y ciclos dentro del límite LP. Compara código con el perfil y
comprueba la forma de despacho indirecto, PC, pila, registros y retorno.
Posición y caché pueden cambiar; los restantes campos deben permanecer iguales.
Se acepta una caché ya coincidente o un payload preexistente únicamente como
consistencia, sin atribuir una lectura nueva. Un pin de código suministrado
no autentica la semántica de todo su cuerpo.

**99 pruebas propias** cubren cierre, objeto ajeno, contador reciclado y overflow,
desplazamiento independiente de capacidad, límites de sector, EOF y solicitud,
posición/retorno incorrectos, cambios de mapa, proceso/sesión mezclados, caché
vacía o previa y bytes ya presentes. Se prueban solicitudes hasta 4096 bytes,
recorte a un sector completo y secuencia regional 256 con el primer exceso.

Los primeros ensayos detectaron dos problemas de fixture/oráculo: una sesión
con formato inválido y un código de rechazo esperado incorrecto. La primera
corrección de sesión aún no actualizaba el identificador de solicitud y fue
rechazada por el contrato de adquisición. El fixture final mantiene coherentes
contexto, solicitud y paquetes; no se relajó ningún validador. Los resultados
anteriores se conservan: 92/94 y 97/98, seguidos de **99/99**.

La regresión completa aprueba **2.731 pruebas, cero fallos y cero omisiones**,
57,129 segundos según JUnit. Las publicaciones operativas finalizaron antes.

| Cobertura | Líneas | Ramas |
|---|---:|---:|
| driver_object | 31/31 (100 %) | Sin ramas instrumentadas |
| driver_transfer | 69/69 (100 %) | 8/8 (100 %) |
| Todas las herramientas | 4.904/4.949 (99,09 %) | 1.369/1.402 (97,65 %) |

Gate 80/80 y Ruff/formato aprobados en 127 archivos del alcance Python de CI.
El job existente descubre los nuevos casos sin originales; no requiere cambiar
el pipeline. Controles finales de enlaces, custodia, hashes y repositorio en
SRC59. Entradas públicas fijadas en SRC52/SRC55/SRC56/SRC57/SRC58 sin cambios.
No se ejecutó CI remota, compilación C++/3DS ni validación física.

## Tareas completadas y siguientes

- [x] **DT-T1:** contrato y vista del pool, fórmula de generación y rechazo de
  filas cerradas/ajenas; cubierto por fixtures y ventanas privadas.
- [x] **DT-T2:** pareja de despacho/posición para un sector con buffer, límites
  de entrada y recibo explícitamente sin prueba de lectura.
- [x] **DT-T3:** perfil privado e inventario estático, dos análisis idénticos
  y custodia verificada; objetos activos siguen sin observarse.
- [x] **DT-T4:** batería propia, regresión, cobertura y documentación trazable.

1. **Puente de apertura y generación:** observar el objeto del driver al retorno
   de apertura y relacionarlo con el handle de SRC58 antes del despacho. Definir
   un perfil de adquisición que respete ocho rangos por pausa; no concatenar
   contratos de 5+4 rangos ni asumir continuidad por igualdad del handle.
   Entregable: EARS, composición y negativos de cierre/reapertura/ABA. Aceptación:
   misma instancia demostrada, o rechazo explícito y cero `Read`.
2. **Referencia backend y sector:** seguir apertura → referencia backend →
   archivo/sector; contrastar los rangos con ISO/MFA. Para caché, registrar cómo
   se llenó el buffer y validar el ABI de copia; para lectura, comprobar su
   finalización y cantidad efectiva. Entregable: perfil y adaptador con casos
   de sector antiguo, archivo ajeno de igual tamaño, error y retorno corto.
3. **Descubrimiento bajo guardia:** obtener pool, objeto, tabla y buffer desde
   la pausa actual. Incluir sondeos/guardados auxiliares en el presupuesto y
   rechazar cambios de identidad, ciclo o mapa. Los dos estados/16 rangos de
   esta pareja no representan el coste total de la futura sesión.
4. **LP-D:** completar el plan antes de ejecutar: ≤48 estados, ≤256 solicitudes
   regionales/hits, 60 segundos activos, 3.600 de pared, 8 GiB de etapa y 10 GiB
   libres mínimos. Español/Normal/Normal desde antes de la carga, sin
   restauraciones intermedias; conservar rechazos, verificar cierre/custodia
   y obtener dos reimportaciones idénticas de la cadena soportada.

Procedencia real, semántica de cámara, F02.07/Q05/G02, dos salas conectadas y
pruebas físicas en New Nintendo 2DS XL permanecen pendientes.
