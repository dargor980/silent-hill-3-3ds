# Inventario de aplicación con plataforma asumida — PT v1

Desarrolla la opción A de la [propuesta](../docs/execution/f02-07-platform-trust-decision.md)
tras la instrucción de continuar. Es un contrato distinto de NC/CI, que conservan
su significado estricto. La plataforma comprende kernel, dyld y Rosetta; confiar
en ella no acredita sus bytes ni el ciclo de vida del emulador.

Historia: como investigador, necesito comprobar la aplicación y señalar qué
parte de la identidad depende de macOS, sin convertir metadatos parciales en
una certificación de todo el proceso.

## Requisitos EARS

- **PT01:** CUANDO se construya el verificador, DEBERÁ recibir configuración
  inmutable del lanzador con perfil/version, identidades de evidencia de política,
  aplicación y plataforma, UUID esperado de caché, cabecera principal e índice de
  su archivo. SI falta cualquier identidad o el perfil no es PT v1, DEBERÁ fallar
  antes de IO. El cliente SHALL NOT configurar el perfil.
- **PT02:** CUANDO se observe, DEBERÁ verificar nacimiento, manifiesto completo
  y loader mediante los componentes existentes; el manifiesto DEBERÁ conservar
  los límites de aplicación y rechazar dos entradas con el mismo device/inode.
- **PT03:** CUANDO una imagen sea de aplicación, DEBERÁ tener mapping de cabecera
  válido, offset cero y exactamente un archivo del manifiesto. SI es desconocida,
  no regular, inaccesible o contradictoria, DEBERÁ rechazar el inventario entero.
- **PT04:** CUANDO una imagen se atribuya a la caché de plataforma, el puerto
  confiable DEBERÁ identificar esa cabecera exacta como miembro mediante evidencia
  del loader. Un intervalo, ruta, flag Mach-O, tag o UUID aislado SHALL NOT ser
  suficiente. El núcleo DEBERÁ exigir UUID esperado y descriptor de caché coherente.
- **PT05:** CUANDO se clasifique la cabecera principal, DEBERÁ corresponder al
  índice de archivo esperado; una imagen de plataforma SHALL NOT satisfacerla.
  La cabecera principal DEBERÁ estar presente en el inventario.
- **PT06:** CUANDO se adquiera el conjunto, DEBERÁ comparar dos pasadas completas
  de origen, manifiesto final, revisión/conjunto final del loader y nacimiento final.
  Cambios de clase, archivo, mapping o descriptor de caché DEBERÁN invalidarlo.
- **PT07:** CUANDO se calcule identidad, DEBERÁ incluir perfil y evidencias en
  dominios propios y campos canónicos; mezclar versiones/evidencias SHALL NOT
  producir la misma identidad de observación.
- **PT08:** SI una observación falla, difiere de la línea base o pierde su sesión,
  DEBERÁ conservar la primera causa y limpiar resultados; llamadas posteriores
  SHALL NOT consultar puertos ni degradarse al perfil alternativo.
- **PT09:** CUANDO se entregue un resultado correcto, DEBERÁ declarar alcance
  application_headers y platform_assumed, con conteos separados. SHALL NOT usar
  `InventoryResult` de NC ni afirmar integridad de caché/AOT, páginas de datos,
  regiones anónimas, peer o permiso de captura.
- **PT10:** CUANDO se valide, DEBERÁ probar perfiles/evidencias mezclados, imagen
  principal ausente, membresía ambigua, omisión, sustitución, cambios entre
  pasadas/muestras, fallos de IO/hash, límites y cierre terminal; conservar NC y AP.

## Diseño y SOLID

`PlatformInventoryGuard` compone `ProcessBirth`, `ManifestGuard`,
`ImageSnapshotSource`, `ImageOriginSource` y `DigestEngine`. El puerto de origen
entrega una unión etiquetada: `application` con `MappedFile`, o `platform_cache`
con `CacheImage`. La rama no seleccionada debe estar vacía. `unknown`, valores
no reconocidos y fallos del puerto rechazan el conjunto; no existe fallback.

`CacheImage` conserva cabecera, base/tamaño de caché y UUID. Estos campos permiten
comprobar consistencia, no demuestran membresía por sí solos. **El proveedor nativo
de ese puerto permanece pendiente** hasta probar PT04 con imágenes reales y una
imagen externa que imite nombre/flags. El núcleo portable no puede autenticar
un doble de pruebas ni el código que implementa su puerto.

La configuración se copia al construir; perfil numérico 1 identifica solamente
`macos_platform_v1`. Cero y valores futuros fallan. Las evidencias SHA-256 no nulas
son identidades fijadas por el lanzador, no firmas ni autorizaciones del cliente.
El manifiesto usa el dominio bundle; tamaño individual 256 MiB, total 512 MiB,
256 archivos. Inventario máximo 2048 imágenes desde [LC/SRC120](image-capacity-v2.md), no vacío, con revisión válida,
direcciones únicas y cabecera principal presente. Se canoniza por dirección.
Todos los testigos de caché deben compartir base/tamaño/UUID en una adquisición.

Secuencia: nacimiento → loader → manifiesto → dos pasadas de orígenes → manifiesto
→ hashes → loader → nacimiento. La instancia conserva una sola línea base y es
de propietario único. Las pasadas iguales no son atómicas ni excluyen ABA.
El resultado no se conecta a AP, al coordinador, al transporte ni a `read_ram`.

Codificación, sin padding ni terminadores: SHA-256 de ASCII
`SH3:platform-files:v1`, perfil u64, evidencia de política/aplicación/plataforma
(32 bytes cada una), UUID esperado (16), cabecera principal u64, índice u64,
cantidad de archivos u64; por archivo, índice y siete campos `FileObject` como
u64 little endian y digest de 32 bytes. Segundo dominio ASCII
`SH3:platform-images:v1`, digest anterior, revisión y cantidad u64; por imagen,
tipo y cabecera u64; aplicación: tamaño, offset e índice de archivo u64;
plataforma: base/tamaño u64 y UUID de 16 bytes. Tipos: aplicación=1, caché=2.
La clave de proceso viaja aparte y se compara en cada frontera.

## Tareas detalladas

- [x] **PT-T1 / PT01–09:** implementar configuración y resultado específicos,
  puerto de origen, composición terminal y codificación. Reutilizar componentes
  existentes, sin modificar NC/AP ni publicar un comando de selección remota.
- [x] **PT-T2 / PT10:** fixtures de mezcla aplicación/caché y negativas por cada
  frontera; vector de bytes independiente, cuatro modalidades y controles de
  regresión. Integrar targets al pipeline y publicar custodia/resultados.
- [x] **PT-T3 / PT04:** implementar y probar un origen nativo que identifique
  miembros exactos del loader/cache, sin ruta/tag/UUID aislado; verificar en
  candidato testconfig y ante imagen externa. Clasificar dyld y bibliotecas del
  sistema fuera de caché mediante un contrato explícito, sin excepción genérica.
  [PO v1](native-platform-origin-v1.md) implementa el adaptador y sus pruebas;
  SRC102 valida el arranque pero rechaza la salida por una biblioteca universal
  con offset 16384. Sigue PO-T3b; PT v1 conserva la restricción de offset cero.
- [x] **PT-T4 / PT02,06,09:** componer manifiesto de candidato, nacimiento y eventos
  reales, medir adquisición/revalidación y entregar evidencia del alcance nuevo.
  Declarar AOT/JIT de Rosetta asumidos como plataforma; no marcarlos verificados.
- [ ] **PT-T5 / IP-NATIVE3,AP:** integrar diagnóstico y peer en candidato nuevo,
  sin habilitar captura hasta completar gates del emulador. Probar perfiles
  cruzados y que fallos nunca activen permisos ni el perfil alternativo.

Actualización SRC103: [MS v1 / PT v2](macho-slice-binding-v1.md) completa la
vinculación universal y las dos pasadas de arranque/salida del candidato.
PT-T3 y PO-T3/3b completas; el perfil v1 conserva offset cero y sus vectores.
Sigue PT-T4: manifiesto esperado y costes. [Evidencia de ejecución](../docs/execution/f02-07-macho-slices.md).


Actualización SRC104: [LM v1](platform-launch-manifest-v1.md) completa PT-T4.
Manifiesto previo de 26 archivos y tres muestras por sesión de arranque/salida,
con cuatro negativos reales. Sigue PT-T5: integrar diagnóstico/peer y hacer
cumplir presupuesto provisional de 5 s inicial/2 s revalidación, con cancelación
externa al hilo de emulación. Captura cerrada. [Informe](../docs/execution/f02-07-launch-manifest.md).

Actualización SRC105: [PD v1](platform-diagnostic-v1.md) completa PT-T5a,
contrato tipado PT v2 y consumidor sin autenticación implícita. Seis mensajes
reales de testconfig y controles de mezcla de perfil/evidencia. PT-T5 sigue
abierto por peer/sesión y ejecución con deadline/cancelación; captura cerrada.
[Informe](../docs/execution/f02-07-platform-diagnostic.md).

Actualización SRC106: [PS v1](diagnostic-peer-v1.md) completa PT-T5b / PD-T4,
peer nativo y sesión ligada al canal. Nueve testconfig privados, tres muestras
positivas y ocho controles terminales. Sigue PT-T5c con presupuesto completo,
cancelación fuera del hilo CPU y gates runtime. Captura cerrada.
[Informe](../docs/execution/f02-07-diagnostic-peer.md).

SRC107 completa DW-T1 / PT-T5c.1 del [ejecutor DW](diagnostic-worker-v1.md).
Presupuesto y cancelación están probados en el núcleo con proveedores sintéticos;
la preparación/lectura/hash nativa y guardias del emulador siguen pendientes.
PT-T5c conserva su estado abierto; no se habilita captura.
