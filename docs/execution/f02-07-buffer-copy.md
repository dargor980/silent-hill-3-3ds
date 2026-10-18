# F02.07 — Copia de buffer y retorno del driver

Fecha: 2026-10-18. SRC63 de `camera-resource-link-eu/origin/load-provenance/LP-C`.
Continúa [SRC62](f02-07-backend-completion.md). Contrato [CP01–CP08](../../schemas/buffer-copy-v1.md)
y [evidencia](../compatibility/buffer-copy-evidence.json).

## Resultado

El [adaptador puro](../../tools/inspectors/buffer_copy.py) enlaza los extremos
del dispatch, las tres pausas BC y la llamada/retorno de copia: **siete estados,
56 solicitudes regionales**, antes del descubrimiento. Conserva identidad,
secuencia y mapas originales, compara el buffer completo y verifica que sus
bytes llegan al destino y permanecen allí al retornar al dispatch.

El resultado acredita consistencia entre evidencias suministradas. Mantiene
cero `Read`, vínculos y capacidades y deja pendientes apertura, continuidad,
autenticación de ejecución, origen físico y captura real. No prueba la ausencia
de escrituras fuera del rango de destino capturado. Un destino que ya contenía
el resultado se admite y se declara sin atribuirle una escritura nueva.

## Hallazgos y decisiones

- La función de copia devuelve el **puntero del destino**. El helper y el lector
  exterior devuelven la **cantidad de bytes**; esta cantidad incrementa la
  posición del driver. Se validan ambos retornos con sus unidades correspondientes.
- La fuente de copia es el buffer más el offset del recurso dentro del sector.
  Se exige longitud exacta, destino coherente con argumentos guardados y buffer
  idéntico desde el éxito del backend hasta retornar de la copia, incluido padding.
- El helper actualiza el índice de caché antes de copiar. La posición del driver
  solo avanza al finalizar el lector. Se acepta exclusivamente ese patrón.
- El perfil privado relaciona dos frames de pila mediante sus prólogos y el
  retorno guardado del helper. El frame debe contener los argumentos capturados.
- Tanto destino como buffer deben estar físicamente separados de los controles
  observados en cualquier pausa. También se comprueban alias con código que solo
  aparece en las pausas de copia.

El contrato DT de dos pausas exige secuencias contiguas. Sus extremos ya no son
contiguos al insertar las cinco pausas interiores: el nuevo contrato reutiliza
sus modelos y `inspect_driver` para validar las mismas relaciones de extremos,
sin renumerar ni fabricar paquetes. Las comprobaciones de pool/generación en
los extremos no demuestran continuidad entre ellos. Los argumentos exteriores
y del helper se comparan en frames separados.

Se hereda el subconjunto BC: archivo normal, un sector, fallo de caché y aceptación
sin progreso temprano del worker. Resolver esa carrera y vigilar liberación,
reasignación y restauraciones sigue siendo parte del perfil conjunto pendiente.

## Evidencia estática y custodia

Se contrastaron **cuatro ventanas / 1.244 bytes** y **22 instrucciones** entre
ELF y estado: helper de sector, copiador, lector y dispatch. Se revalidaron las
15 ventanas previas y las identidades ISO, ELF, catálogo, contenedor, recurso y
sector válido. Las fuentes PCSX2 fijadas conservan sus hashes, sin copiar su
implementación al runtime. El estado posterior tiene pools inactivos; no se
promueve a inicio válido de captura ni a observación de una copia activa.

Plan privado creado sin sobrescribir, directorio 0700 y archivo 0600. Ventanas,
direcciones y registros originales permanecen privados; el repositorio publica
solo contratos, código/fixtures propios y metadatos. Lectores cerrados antes de
publicar, con fuentes intactas. Dos análisis producen informes idénticos de
**3.301 bytes**, SHA-256
`34cbf8596f46961dd67e13d57df7bae9f742219e25b511783b84620863d6498d`.

## Implementación y validación

`CopyProfile` agrupa perfiles BC/DT, copiador y sitios de llamada. El adaptador
separa validación de entradas, enlace de pausas y reconciliación del recorrido;
reutiliza adquisición y modelos sin I/O ni dependencias nuevas. Los contratos
históricos, PCSX2 y runtime Nintendo permanecen iguales.

Las pruebas propias cubren retornos, cantidad, offset no alineado, último sector
parcial, buffer sustituido, destino preexistente, alias físico, código y pila,
generación, mapas, identidad y límites de secuencias/ciclos. El pipeline existente
descubre las pruebas Python sin originales; no requiere cambiar los builds.

El primer ensayo aprobó **66/66** casos. La revisión añadió cinco casos sobre
espacio del frame, alias buffer/copiador y argumentos exteriores/retorno guardado;
el ensayo final aprobó **71/71**. No hubo fallos de pruebas ni relajación de gates.

Regresión completa: **3.047 aprobadas**, cero fallos, errores u omisiones;
102,716 segundos según JUnit. Los informes operativos terminaron antes de la
suite y no se editaron fuentes ni documentación durante su ejecución.

| Cobertura | Líneas | Ramas |
|---|---:|---:|
| buffer_copy | 115/115 (100 %) | 26/26 (100 %) |
| Todas las herramientas | 5.238/5.283 (99,15 %) | 1.433/1.466 (97,75 %) |

Gate 80/80, Ruff y formato aprobados en 135 archivos Python. Controles del
repositorio sin errores; hashes, custodia, enlaces y diff verificados. Las entradas
públicas fijadas de SRC55–SRC62 permanecen intactas.

No se ejecutó PCSX2, CI remota, compilación C++/3DS ni prueba física.

## Tareas y siguiente unidad

- [x] **CP-T1 / CP01,05:** trazado de copiador, frames y retornos diferenciados.
- [x] **CP-T2 / CP02–06:** siete pausas originales, invariantes, copia y destino.
- [x] **CP-T3 / CP07:** dos análisis privados iguales y fuentes intactas.
- [x] **CP-T4 / CP08:** regresión, cobertura y gates con trazabilidad final.

1. **Perfil conjunto y continuidad:** componer catálogo, apertura, pools y este
   recorrido sin alterar secuencias ni reutilizar pausas de estados distintos.
   Resolver el progreso temprano del worker mediante puntos internos o contrato
   adicional. Observar cierre/reasignación/restauración bajo guardia y rechazar
   huecos; no convertir coincidencia de extremos en continuidad acreditada.
2. **Descubrimiento y presupuesto:** derivar punteros de la nueva sesión,
   incluir sondeos auxiliares y deduplicar únicamente observaciones del mismo
   estado real. Fijar ≤48 estados y ≤256 solicitudes regionales/hits.
3. **LP-D:** iniciar antes de la carga, español/Normal/Normal, sin restaurar
   entre puntos; 60 segundos activos, 3.600 de pared, 8 GiB de etapa y 10 GiB libres.
   Conservar rechazos, cierre/custodia y dos reimportaciones iguales.

F02.07/Q05/G02, procedencia real, semántica de cámara, dos salas conectadas y
validación física en New Nintendo 2DS XL siguen pendientes.
