# F02.07 — Finalización backend y buffer de sector

Fecha: 2026-10-18. SRC62 de `camera-resource-link-eu/origin/load-provenance/LP-C`.
Continúa [SRC61](f02-07-backend-sector.md). Contrato [BC01–BC08](../../schemas/backend-completion-v1.md)
y [evidencia](../compatibility/backend-completion-evidence.json).

## Resultado

El nuevo [adaptador puro](../../tools/inspectors/backend_completion.py) enlaza
solicitud, aceptación y finalización suministradas. Valida retorno, estado y
cantidad completada, posición y buffer; contrasta el sector válido completo
y el recurso contenido con sus hashes independientes. Mantiene cero eventos
`Read`, vínculos y capacidades: una relación consistente entre estados no prueba
ejecución, continuidad ni una lectura nueva.

Se compone BS con dos pausas adicionales de ocho rangos: **tres estados y 24
solicitudes regionales**, sin contar descubrimiento. La segunda y tercera
incluyen el buffer de 2048 bytes y omiten la tabla de dispositivo, ya observada
en la primera. El mapa de controles comunes permanece estable; se rechaza
solapamiento físico del buffer con cualquier control, incluida esa tabla.

## Hallazgos y alcance

- El backend devuelve una cantidad **en sectores** al aceptar la solicitud.
  Esa aceptación no es su finalización. La consulta posterior devuelve estado.
- La rutina de progreso puede avanzar posición tanto en éxito como en error.
  Se exige éxito, un sector completado y avance exacto; posición aislada no basta.
- El stream conserva posición relativa en sectores y contabiliza el llenado
  en bytes. Para esta solicitud debe terminar con 2048 bytes y un sector.
  Su tamaño mutable se contrasta como longitud de solicitud, no identidad de archivo.
- Se exige que el descriptor de disco mantenga identidad/extensión y termine
  con posición, cantidad y buffer coherentes, sin solicitud pendiente. La
  liberación del wrapper backend deja un alias en el stream que no se dereferencia.
- El hash del sector cubre todos sus bytes válidos de archivo, incluidos los
  que quedan fuera del recurso. El padding del último sector parcial se excluye.
  Un buffer ya coincidente al aceptar la solicitud se declara expresamente.

El subconjunto exige que el worker no haya progresado todavía al capturar la
aceptación. Una captura ya avanzada se rechaza como fuera de perfil; no se
diagnostica como fallo del juego. El perfil conjunto deberá resolver esta
carrera con puntos internos o un contrato adicional. Driver, argumentos y pila
permanecen iguales; la última pausa precede a la actualización de caché y a la
copia. No se acredita todavía pertenencia a pools, continuidad ni origen físico
de los bytes del buffer. La tabla de dispositivo tampoco se observa continuamente.

## Evidencia estática y custodia

Se contrastaron **15 ventanas / 3.608 bytes** y **22 instrucciones** con ELF y
estado, además de las 19 ventanas anteriores. Se revalidaron ISO, ELF, catálogo,
contenedor, recurso y sector completo. Las fuentes PCSX2 ya fijadas permanecen
iguales, sin incorporar su implementación al proyecto. El estado posterior
conserva los pools inactivos: no aporta una lectura activa ni sirve como inicio
de una captura nueva.

El plan privado usa directorio 0700 y archivo 0600, creados sin sobrescribir.
Los informes públicos solo contienen metadatos. Los originales, direcciones,
registros y ventanas de código permanecen privados. Los lectores se cierran
antes de publicar los informes; se verifican fuentes intactas.

Dos análisis generan informes idénticos de **4.729 bytes**, SHA-256
`628e74cf1c1d918f31544064ad6592896ff102b5ecc0b16b189414f5803d31e6`.

## Implementación y pruebas

`CompletionProfile` delimita la llamada de consulta dentro del código de BS.
El adaptador recibe valores y evidencias, reutiliza BS/LF y devuelve metadatos.
La lectura de ISO, la adquisición y la custodia siguen en componentes separados.
No añade dependencias ni modifica los módulos históricos, PCSX2 o runtime Nintendo.

Las pruebas propias cubren estados de error/cancelación, lectura corta, cantidades
y unidades, sector ajeno con recurso coincidente, padding, buffer preexistente,
solapamiento y mapas, ABI, slots, identidad y límites de secuencia/ciclos.
El job Python existente las descubre sin archivos originales. No se requiere
modificar el pipeline de compilación para este adaptador Python.

El primer ensayo ejecutó 94 casos: 93 pasaron y uno falló por un atributo
inexistente en el fixture de cambio de mapa. Se corrigió el fixture y pasaron
94/94. La revisión añadió el solapamiento con la tabla de dispositivo observada
solo en la primera pausa y amplió la protección del adaptador: **95/95**.

Regresión completa: **2.976 aprobadas**, cero fallos, errores u omisiones;
83,753 segundos según JUnit. Los dos informes operativos terminaron antes de
iniciar la suite, sin mutaciones del repositorio durante las pruebas.

| Cobertura | Líneas | Ramas |
|---|---:|---:|
| backend_completion | 87/87 (100 %) | 18/18 (100 %) |
| Todas las herramientas | 5.123/5.168 (99,13 %) | 1.407/1.440 (97,71 %) |

Gate 80/80, Ruff y formato aprobados en 133 archivos Python. Controles de
repositorio sin errores; enlaces, hashes, custodia y diff verificados. Los pins
históricos se comprueban con sus revisiones aplicables; `observer_state` utiliza
el pin posterior de SRC53, que sustituyó al de SRC52 antes de esta unidad.

No se ejecutó PCSX2, CI remota, compilación C++/3DS ni prueba física.

## Tareas y siguientes pasos

- [x] **BC-T1 / BC01–04:** recorrido, unidades y perfil de estados/contadores.
- [x] **BC-T2 / BC02–06:** composición, identidad, estabilidad y hashes de buffer.
- [x] **BC-T3 / BC07:** dos análisis idénticos, plan privado y fuentes intactas.
- [x] **BC-T4 / BC08:** regresión, cobertura, gates y trazabilidad final.

1. **Copia al destino:** fijar ABI de la copia desde buffer, offset dentro del
   sector, longitud y retorno; contrastar bytes del destino y enlazar con DT.
   Probar fuente/destino ajenos, copia parcial, buffer sustituido y destino
   preexistente. Reutilizar pausas solo cuando pertenezcan al mismo estado real.
2. **Perfil conjunto y continuidad:** unir catálogo, apertura, pools, solicitud,
   finalización y copia. Resolver progreso temprano del worker y descubrir
   punteros bajo guardia. Observar cierre/reasignación/restauración; no atribuir
   continuidad a extremos idénticos. Presupuestar también sondeos auxiliares.
3. **LP-D:** captura desde antes de la carga, español/Normal/Normal, sin restaurar
   entre puntos; ≤48 estados, ≤256 solicitudes regionales/hits, 60 segundos
   activos, 3.600 de pared, 8 GiB de etapa y 10 GiB libres. Conservar rechazos,
   cierre/custodia y dos reimportaciones iguales.

F02.07/Q05/G02, procedencia real, semántica de cámara, dos salas conectadas y
validación física en New Nintendo 2DS XL siguen pendientes.
