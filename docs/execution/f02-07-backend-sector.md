# F02.07 — Referencia backend, archivo y sector

Fecha: 2026-10-18. SRC61 de `camera-resource-link-eu/origin/load-provenance/LP-C`.
Continúa [SRC60](f02-07-open-driver.md). Contrato [BS01–BS08](../../schemas/backend-sector-v1.md)
y [evidencia](../compatibility/backend-sector-evidence.json).

## Resultado

Se trazó la referencia del driver a través de backend, stream, file y descriptor
de disco. El nuevo [validador puro](../../tools/inspectors/backend_sector.py)
contrasta la cadena suministrada, tamaño y extensión ISO, posición y solicitud
de un sector hacia el buffer. Rechaza un archivo de igual tamaño con otro sector
inicial, un sector antiguo, registros libres y argumentos incompatibles.

El perfil usa **una pausa de ocho rangos** antes de solicitar el sector durante
un fallo de caché. No incluye las cabeceras de los pools ni acredita pertenencia,
generación o continuidad. Tampoco prueba apertura, finalización, bytes del buffer
o copia al destino. El recibo conserva cero `Read`, vínculos y capacidades.
La revalidación ISO del análisis privado no convierte un recibo suministrado en
captura auténtica. LP-C sigue parcial; el perfil conjunto y LP-D están pendientes.

## Hallazgos y decisiones

- El driver mantiene posición en **bytes**; el backend mantiene posición en
  **sectores de 2048 bytes** y conserva el tamaño del archivo en bytes.
- El backend apunta al stream, este a un registro file y ese registro a una
  tabla de dispositivo y al descriptor de disco. El descriptor conserva sector
  inicial y tamaño; el camino de envío suma sector inicial y posición de disco.
- La preparación de lectura sobrescribe el tamaño del stream. Ese campo no
  identifica el archivo. Su posición y la del disco pueden conservar valores
  de la operación previa hasta que se propague la solicitud; el validador usa
  la posición backend en el punto elegido.
- El subconjunto admite archivos normales, sin el modo especial de tamaño
  ilimitado. Limita tamaño a `2**31 - 2048` para que el redondeo con signo a
  sectores no desborde. El buffer debe estar alineado a 64 bytes.

Se contrastaron **19 ventanas / 3.976 bytes** y 19 instrucciones entre ELF y
estado. La tabla de dispositivo de 64 bytes coincide con ELF; su registro y
selección predeterminada coinciden en el estado. También se revalidaron las
cuatro ventanas de SRC60 y las identidades ISO, ELF, catálogo, contenedor y
payload. ADDIU, MOVN y SRA se contrastan con `R5900OpcodeImpl.cpp` de la revisión
PCSX2 ya fijada, sin copiar implementación; ambas copias conservan el hash
`6ae749a7e3a297a291f1844d2f96a17bf7c53a9c6f6f4ab4ddab27781a78c2b4`.

El inventario del estado posterior muestra **16 backend, 40 stream, 40 disco y
40 registros file sin actividad**. No se promueven esos registros a archivos
abiertos ni se reutilizan como inicio de captura. Las direcciones y los bytes
originales permanecen privados.

Dos análisis generan informes idénticos de **4.918 bytes**, SHA-256
`5c79dcdd958f1db9166e7135b106a4edf9183254c34a9edece1903a9bede99cb`.
Plan creado sin sobrescritura, directorio 0700 y archivo 0600; fuentes intactas,
lectores cerrados antes de publicar. Los sondeos para descubrir direcciones
actuales se presupuestarán aparte de esta pausa y sus ocho solicitudes.

## Implementación y pruebas

`DiscSource` modela la extensión suministrada; `BackendProfile` fija llamador,
llamada y tabla. El módulo reutiliza `DriverRequest` y LF para validar bytes,
CPU y mapas. No incorpora I/O ni dependencias y no cambia los módulos históricos,
PCSX2 o el runtime Nintendo. La responsabilidad de adquirir/custodiar sigue en
los adaptadores existentes; finalización y copia requieren sus propios contratos.

Las **87 pruebas propias** cubren cadena rota, archivo/sector ajenos, estados,
unidades, caché coincidente, buffer, ABI, mapas, último sector parcial y límites
de extensión, redondeo y secuencia regional 256. El primer ensayo aprobó 86;
la revisión del redondeo añadió el límite y su prueba, con **87/87** posteriores.
No hubo fallos de pruebas ni relajación de umbrales.

Regresión completa: **2.881 aprobadas**, cero fallos, errores u omisiones;
71,605 segundos según JUnit. Los informes operativos finalizaron antes de la suite.

| Cobertura | Líneas | Ramas |
|---|---:|---:|
| backend_sector | 76/76 (100 %) | 10/10 (100 %) |
| Todas las herramientas | 5.036/5.081 (99,11 %) | 1.389/1.422 (97,68 %) |

Gate 80/80 y Ruff/formato aprobados en 131 archivos Python. El job existente
descubre los tests sin originales; no requiere cambiar el pipeline. Controles
finales de repositorio, enlaces, hashes y custodia registrados en SRC61.
No se ejecutó PCSX2, CI remota, compilación C++/3DS ni prueba física.

## Tareas completadas y siguientes

- [x] **BS-T1 / BS01–04:** recorrido estático, modelos y contraste de archivo/extensión.
- [x] **BS-T2 / BS05–06:** solicitud de sector, argumentos y recibo mínimo sin `Read`.
- [x] **BS-T3 / BS07:** perfil privado y dos análisis iguales con fuentes conservadas.
- [x] **BS-T4 / BS08:** pruebas, regresión, cobertura y trazabilidad.

1. **Finalización y llenado de buffer:** observar estados y contadores del backend
   antes/después; exigir sector inicial, cantidad solicitada y cantidad completada
   coherentes, y contrastar bytes válidos del buffer con ISO. Probar error,
   cancelación, retorno corto y buffer de otra lectura. No inferir éxito solo
   del estado final o hash del recurso.
2. **Copia al destino:** fijar ABI y retorno de la copia desde buffer, incluidos
   offset dentro del sector, cantidad y destino; enlazar con DT. Probar fuente
   ajena, destino preexistente y copia parcial. Mantener límites de adquisición.
3. **Perfil conjunto y continuidad:** unir catálogo, apertura, pools, solicitud,
   finalización y copia; observar cierre/reasignación/restauración y descubrir
   punteros bajo guardia. Contar estados y solicitudes auxiliares, rechazar huecos.
4. **LP-D:** ejecutar desde antes de la carga, español/Normal/Normal, sin restaurar
   entre puntos; ≤48 estados, ≤256 solicitudes regionales/hits, 60 segundos
   activos, 3.600 de pared, 8 GiB de etapa y 10 GiB libres. Conservar rechazos,
   cierre/custodia y dos reimportaciones iguales.

Procedencia real, semántica de cámara, F02.07/Q05/G02, dos salas conectadas y
validación física en New Nintendo 2DS XL siguen pendientes.
