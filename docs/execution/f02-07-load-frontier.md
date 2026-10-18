# F02.07 — Fronteras de lectura y evidencia multirrango

Unidad: `origin/load-provenance/LP-C`, pasos 1–2. Fecha: 2026-10-18.
Estado: **rutas estáticas y validadores completados; vínculo con archivo activo
y adquisición multirrango pendientes**.
Contrato [LF01–LF08](../../schemas/load-frontier-v1.md).
[Evidencia SRC56](../compatibility/load-frontier-evidence.json).

## Hallazgos y alcance

Se compararon **11 ventanas, 3.124 bytes**, del ELF y el estado fijados en
SRC55. Coinciden íntegramente. La ruta candidata encadena apertura, búsqueda
de descriptor, posicionamiento, transferencia y entrega. La interpretación
del flujo distingue una ruta de destino directo, otra con transferencia
intermedia y rutas de acierto/fallo de caché de sectores. También hay recortes
de solicitud al final del recurso. Estas son posibilidades del código, no
las rutas demostradas de una ejecución nueva.

Se fijaron tres sitios de llamada directa y dos de despacho indirecto. Dos
sitios directos usan los argumentos de transferencia que valida esta unidad;
el tercero es candidato de copia desde caché y necesita otro contrato ABI.
La rama de acierto de caché alcanza la copia sin repetir la operación previa
de obtención del sector. Por eso un retorno con tamaño correcto y payload
coincidente no prueba una nueva lectura de disco.

El objeto residual inspeccionado tiene descriptor cerrado y campos de tamaño
y posición vacíos. Su tabla de despacho ayuda a localizar código, pero no
vincula un archivo activo con el candidato. Se preserva esta limitación en el
plan privado y en el informe: no se produce ningún evento `Read` para el modelo
de procedencia ni se considera satisfecha LP09.

Dos análisis de los mismos originales producen un informe idéntico de
3.387 bytes, SHA-256
`a3c4d88704752f1ae9e91eb0b0d304ac7e4ff3e52bc0a98d452d88f900b2364e`.
Se verificaron de nuevo la ISO completa, el ELF, los planes anteriores y el
estado. El lector ISO se cierra antes de publicar, y el estado/evidencia previa
se vuelven a comprobar. Los planes privados no se sobrescriben. Son dos
análisis estáticos, sin nueva sesión de PCSX2.

## Implementación y separación de responsabilidades

[mapped_pause](../../tools/inspectors/mapped_pause.py) valida de uno a ocho
rangos suministrados de una misma pausa. Cada rango conserva su plan AC y tres
paquetes. Exige un estado común, hash, slot, identidad, PC y ciclo coherentes;
contrasta todos los bytes con RAM y verifica mapas AC/MP, incluso al cruzar
páginas. Las anclas deben coincidir, y una página compartida entre dos rangos
no puede aportar traducciones distintas. Los resultados privados se devuelven
tipados; no se abre un socket ni se controla el emulador.

[load_call](../../tools/inspectors/load_call.py) usa ese adaptador para dos
pausas con rangos de código y destino. Comprueba secuencia, slots distintos,
mapas estables en ambos puntos, ciclos, SP y RA. Fija doce bytes: JAL directo,
delay slot e instrucción en el punto de retorno. Así también exige la página
del retorno cuando cruza un límite; no afirma que esa instrucción se ejecutó.
Admite NOP o una copia DADDU acotada a GPR6 en el slot y rechaza otras formas.

El tamaño se calcula después del efecto del slot; destino y solicitud deben
coincidir con el rango observado, y GPR2 debe devolver exactamente esa cantidad.
Se rechazan errores, retornos cortos, códigos alterados, cambios de mapa y
mezclas de estados. Se permite un destino sin cambios, porque una llamada
coherente no demuestra por sí sola escritura nueva ni procedencia.

El verificador cubre código de llamada/slot/retorno y destino, no el cuerpo
completo del destinatario. Los recibos mantienen autenticación no provista,
archivo/disco/ejecución real sin verificar, cero eventos `Read`, vínculos y
capacidades vacíos. Custodia, adquisición, identidad del archivo y publicación
continúan en adaptadores separados. No se añadieron dependencias ni se cambió
el runtime Nintendo o el build de PCSX2.

## Validación

**68 casos propios nuevos** cubren argumentos y delay slot, tamaños de 1,
32 y 4.096 bytes, retorno corto/error, destino sin cambios, identidad,
estados/paquetes alterados, uno/ocho rangos y primer exceso, código/datos
en dos páginas, alias inesperado, anclas y traducciones contradictorias,
retorno en otra página y el límite exacto de ciclos más su primer exceso.

La regresión final aprueba **2.433 pruebas sin fallos ni omisiones**; JUnit
registra 32,736 segundos. La primera regresión conserva un fallo del control
de custodia: el análisis operativo publicó el informe durante el recorrido
de archivos, después de que se tomara el inventario Git de ignorados. El
control independiente pasó con archivos estables. Se completó la publicación
y se repitió la regresión sin escrituras concurrentes, sin debilitar el control.

| Cobertura | Líneas | Ramas |
|---|---:|---:|
| mapped_pause | 50/50 (100 %) | 8/8 (100 %) |
| load_call | 31/31 (100 %) | 2/2 (100 %) |
| Total herramientas | 4.565/4.610 (99,02 %) | 1.325/1.358 (97,57 %) |

Pasan el gate independiente 80/80, Ruff/formato en los 118 archivos del alcance
Python de CI, los controles de repositorio y `git diff --check`. El job
existente descubre estos módulos y fixtures sin originales del juego. No se
ejecutó CI remota ni una nueva compilación C++/3DS o suite de proveedores.

## Siguiente tarea: vínculo de descriptor y captura multirrango

1. **Descriptor activo y archivo:** seguir apertura y posición hasta la llamada
   candidata. Fijar rango del archivo, descriptor y su generación, resultado
   de apertura, tamaño solicitado/real y cambios de posición. Capturar las
   estructuras necesarias mientras están activas; rechazar objetos cerrados,
   reciclados o vinculados solo por nombre. Entregable: contrato y adaptador
   puro que vinculen el descriptor al origen ISO/MFA fijado en SRC55.
2. **Ruta seleccionada:** observar el destinatario indirecto y el estado del
   sector. Si hay acierto de caché, obtener procedencia del bloque previo y
   validar la copia; si hay fallo, fijar la operación que completa la lectura.
   No traducir automáticamente una transferencia coherente a `Read`. Añadir
   fixtures de descriptor reciclado, posición distinta, lectura corta, caché
   sin origen y copia no soportada.
3. **Adquisición multirrango:** extender la coordinación AC para obtener código,
   datos y metadatos requeridos contra un mismo estado/slot, con guardia de
   proceso, PINE, mapas y custodia antes/después. No concatenar estados
   independientes como si fueran una pausa. Mantener máximo de 256 solicitudes
   regionales por sesión y comprobar el consumo del plan antes de iniciarlo.
4. **LP-D:** preparar perfil español/Normal/Normal desde antes de la carga,
   con slots nuevos y los límites de LP. La entrada SRC53 ya es posterior y
   el objeto cerrado de esta inspección no la reemplaza. Capturar la cadena
   soportada, conservar rechazos, reimportar dos veces y verificar cierre.

LP-C sigue parcial. Procedencia real, semántica de cámara, F02.07/Q05/G02,
dos salas y pruebas físicas en New Nintendo 2DS XL permanecen pendientes.
