# F02.07 — Unión de intervalos y dependencias (SRC98)

NR-T1–3 completa el planificador estructural de CI-T4 según
[NR01–NR10](../../schemas/native-range-plan-v1.md). Reproduce los dos censos de
[SRC97](f02-07-native-layout.md) conservando todos sus segmentos y dependencias.
Todavía no verifica todas las páginas ni asocia los objetos transformados.

El núcleo portable separa planificación, adquisición y prueba de origen: recibe
descripciones de rangos, calcula intervalos disjuntos y devuelve las dependencias
por propietario. No hace I/O ni modifica CacheRangeGuard. Conserva segmentos
reservados/vacíos, divide colas zero-fill y señala contradicciones de permisos o
clasificación. Canoniza por propietario; distingue identificadores Mach-O/AOT.
Aceptar el dominio AOT no equivale a haber enumerado sus mappings reales.

## Resultado del censo conservado

| Medida | Inicio | Salida |
| --- | ---: | ---: |
| Segmentos de entrada | 2588 | 3020 |
| Intervalos disjuntos | 2092 | 2442 |
| Dependencias de intervalos a segmentos | 2618 | 3054 |
| Bytes declarados, con aliases y reservas | 100943383287 | 115698350103 |
| Bytes reservados sin permisos | 4294967296 | 4294967296 |
| Bytes virtuales únicos activos | 2466974455 | 2550806551 |
| Páginas virtuales únicas tocadas, 4 KiB | 603112 | 623654 |
| Bytes únicos en colas zero-fill declaradas | 217388760 | 217418696 |
| Bytes con conflicto | 0 | 0 |
| Tiempo de planificación, dos reproducciones | 0,552 / 0,359 ms | 0,515 / 0,402 ms |

Un oráculo independiente por intersección de límites compara cada intervalo y
cada propietario del resultado C++, dos veces por fase. La salida es idéntica
salvo tiempos; se verifica el hash del log original. El oráculo de los tests
sintéticos también compara byte a byte 400 conjuntos y sus permutaciones.

Estos bytes describen una unión de direcciones virtuales de las imágenes censadas,
no RAM física ni la cobertura del proceso completo. Los tiempos excluyen lectura
de páginas, comprobación de origen y hashing. No sustituyen los 106 s de SRC96.
Las reservas no se recorren; la clasificación zero-fill no afirma que el contenido
actual permanezca en cero. Esta tarea no ejecutó PCSX2 ni leyó memoria viva.

## Los catorce objetos pendientes

En ambos censos, cada objeto desconocido presenta un único valor de
`dirección - offset del objeto` entre todos sus puntos observados. Son los mismos
14 identificadores entre fases: siete agrupan __DATA_CONST y siete los otros
segmentos de datos, incluido __CTF. Esta regularidad no establece qué archivo
respalda cada objeto ni acredita sus páginas interiores.

El [pager de regiones compartidas de XNU](https://github.com/apple-oss-distributions/xnu/blob/f6217f891ac0bb64f3d375211650a4c1ff8ca1ea/osfmk/vm/vm_shared_region_pager.c#L66)
publicado por Apple transforma páginas desde un objeto respaldado por la caché y
mantiene limpias las páginas resultantes. Su relación con el objeto de origen es
interna al kernel. Es una explicación compatible con los puntos observados,
**no una asociación demostrada** ni una identificación del kernel instalado.

La [consulta de páginas de XNU](https://github.com/apple-oss-distributions/xnu/blob/f6217f891ac0bb64f3d375211650a4c1ff8ca1ea/osfmk/vm/vm_map.c#L19847)
devuelve el identificador del objeto encontrado y su offset. El puerto actual
no obtiene el vínculo interno del pager al archivo. Por tanto, se conserva el
rechazo de objetos desconocidos: external/clean, el nombre del segmento y el
número de grupos no se convierten en una excepción de confianza. Se requiere
una prueba adicional para transformaciones, COW y memoria zero-fill.

## Verificación y custodia

- **205 escenarios × cuatro configuraciones = 820 ejecuciones correctas** en
  macOS x86_64: Debug, Release, ASan+UBSan y cobertura. Incluyen los 189 anteriores.
- 16 escenarios nuevos: aliases, solapamientos parciales/anidados, clasificación,
  conflictos, reservas, páginas parciales, dominios, límites, overflow, entrada
  que comparte almacenamiento con salida y fallos de todas las asignaciones.
- Planificador: **100% líneas (75/75), 98,72% ramas (77/78)**. La rama pendiente
  corresponde al límite defensivo de átomos, superior al máximo alcanzable con
  el límite de entradas; no se relaja ningún presupuesto para cubrirla.
- Cuatro regresiones compiladas detectadas: omitir propietarios, omitir bytes,
  omitir la frontera zero-fill y volver a contar una página compartida.
- 122 pruebas Python correctas; Ruff y comprobación de enlaces/repositorio.

El CMake host incorpora los casos al pipeline existente. CI remoto, Linux,
arm64 y detección de fugas no se ejecutaron. Etapas nuevas privadas:
`native-range-stage-v1`, `native-range-replay-v1`, `native-range-mutants-v1`.
Scripts/recibos: `build/f02-07-range-plan/`. Límites supervisados: 10 GiB libres
iniciales/piso y 512 MiB por etapa. Fuentes, perfiles, resultados y fallos
intencionales se conservan. Solo CMake host cambia respecto de las entradas de
código de SRC97; su snapshot anterior se verifica sin reescribirlo.

## Trabajo restante de CI-T4

1. Demostrar el origen de los 14 objetos transformados, separándolo del estado
   mutable de sus páginas; probar sustitución, cambio y origen desconocido.
2. Enumerar mappings AOT fuera del loader y unirlos conservando sus propietarios.
3. Usar el plan para verificar cada página requerida, manteniendo vínculo con
   nacimiento, revisión y archivos verificados antes/después. El plan estructural
   no aporta por sí solo esa continuidad.
4. Medir y acotar el ciclo de adquisición/revalidación antes de IP-NATIVE3.

CI-T4 permanece abierto. No se habilitan Observation, peer, admisión ni captura.
