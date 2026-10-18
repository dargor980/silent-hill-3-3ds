# Backend sector v1 — BS01–BS08

Estado: consistencia de una solicitud de sector suministrada, F02.07/LP-C.

Como investigador quiero seguir la referencia backend hasta el descriptor de
disco y contrastar su extensión con la ISO antes de atribuir una lectura.

## Requisitos EARS

- **BS01:** WHEN se recibe el origen THEN el adaptador SHALL exigir hashes
  canónicos, extensión ISO alineada a 2048, tamaño positivo con signo y recurso
  contenido en un único sector; SHALL rechazar overflow del redondeo con signo
  a sectores y extensiones fuera de imagen (tamaño máximo `2**31 - 2048`).
- **BS02:** WHEN se recibe una pausa THEN el adaptador SHALL validar ocho rangos
  LF `driver,backend,stream,file,device,disc,code,args`, sus longitudes, identidad,
  mapa y bytes, y exigir código/perfil de dispositivo coincidentes.
- **BS03:** WHEN se sigue la cadena THEN el adaptador SHALL exigir referencias
  no nulas/alineadas driver→backend→stream→file→disc y file→device; SHALL rechazar
  registros libres o estados incompatibles con la preparación de una lectura.
- **BS04:** WHEN se contrasta el archivo THEN el adaptador SHALL exigir tamaño
  en bytes y redondeo a sectores coherentes en backend/disco, y LSN inicial igual
  a la extensión ISO suministrada; SHALL rechazar archivos de igual tamaño en
  otra extensión y el modo especial de tamaño ilimitado.
- **BS05:** WHEN se valida la solicitud THEN el adaptador SHALL exigir posición
  del driver en bytes, posición backend en sectores, una solicitud de un sector
  hacia el buffer alineado a 64 y argumentos guardados coherentes; SHALL rechazar
  caché ya correspondiente al sector, sector antiguo y PC ajeno al sitio de llamada.
- **BS06:** WHEN se publica el recibo THEN el adaptador SHALL emitir solo hashes,
  tamaños, conteos y alcance; SHALL declarar pendientes pertenencia a pools,
  generación/continuidad, apertura observada, revalidación de origen, semántica de
  perfiles, finalización, llenado de buffer y captura real, con cero `Read` y capacidades.
- **BS07:** WHEN se fija el perfil operativo THEN la investigación SHALL contrastar
  las ventanas y tabla de dispositivo con ELF/estado y extensión con ISO; SHALL
  repetir el análisis, conservar originales y publicar únicamente metadatos.
- **BS08:** WHEN se verifica la implementación THEN las pruebas SHALL usar datos
  propios y cubrir cadena rota, archivo/sector ajenos, estados, unidades, límites,
  mapas y ABI; SHALL aprobar regresión, cobertura y verificaciones del repositorio.

## Diseño y decisiones

`backend_sector.reconcile_backend_sector(source, request, profile, points)` es
puro. Recibe `DiscSource`, `DriverRequest` y `BackendProfile`; reutiliza LF para
validar una pausa. El origen no contiene nombres ni rutas. El perfil suministrado
incluye la ventana del llamador, la llamada directa y la tabla de dispositivo.

La pausa precede a la solicitud backend de un sector durante un fallo de caché.
El recorrido enlaza objeto del driver (48 bytes), backend (56), stream (72),
file (8), tabla de dispositivo (64) y disco (72), además de código y argumentos
guardados (52). Son ocho rangos; no se añade la cabecera de los pools ni se
afirma pertenencia o generación. No se compone todavía con OD/DT en una sesión.

La posición backend está en sectores y el tamaño de archivo en bytes. El stream
contiene un tamaño que la preparación de lecturas puede sobrescribir: **no** se
usa como identidad del archivo. La identidad suministrada se contrasta con el
tamaño y LSN del descriptor de disco. La posición interna de disco puede conservar
la lectura anterior hasta que se propague la solicitud; no se confunde con la
posición backend que se está validando. Se rechaza el modo especial ilimitado.

El recibo acredita relaciones entre bytes suministrados. No prueba que la llamada
se ejecutó, que el buffer se llenó ni que el dispositivo terminó correctamente.
Las direcciones y registros permanecen en planes/estados privados. Sin nuevas
dependencias, sin I/O en el validador y sin modificar contratos históricos.

## Tareas y aceptación

1. **BS-T1 / BS01–04:** trazar los niveles y unidades; modelar extensión y cadena.
   Aceptación: archivo de igual tamaño con otro LSN se rechaza, cadena completa
   suministrada se diagnostica sin acreditar pools ni continuidad.
2. **BS-T2 / BS05–06:** validar llamada, argumentos y sector solicitado; publicar
   un recibo mínimo. Aceptación: sector antiguo, caché coincidente y buffer no
   alineado se rechazan; el éxito produce cero eventos de lectura.
3. **BS-T3 / BS07:** perfil privado y extensión ISO, dos análisis deterministas.
   Aceptación: hashes intactos, plan sin sobrescritura, directorio 0700/archivo 0600.
4. **BS-T4 / BS08:** negativos y límites, regresión/cobertura y documentación.
   Aceptación: gates aprobados; copia, finalización y adquisición real quedan explícitas.
