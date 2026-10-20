# Manifiesto previo al lanzamiento — LM v1

Detalle de PT-T4. Historia: como investigador necesito que los archivos esperados
procedan del lanzador confiable antes de observar el proceso y medir el coste de
vincular esos archivos con todas las cabeceras cargadas mediante PT v2.

## Requisitos EARS

- **LM01:** CUANDO prepare una ejecución, el lanzador DEBERÁ fijar raíces, nombres,
  tamaños, SHA-256 completos, índice del ejecutable, UUID de caché y evidencias de
  política/plataforma antes de iniciar el candidato. El propio observador DEBERÁ
  estar incluido. SHALL NOT aprender hashes esperados del proceso observado.
- **LM02:** CUANDO lea la configuración, DEBERÁ comprobar tamaño máximo 1 MiB,
  identidad del archivo antes/después, lecturas exactas, EOF y SHA-256 esperado
  proporcionado por el lanzador. La decodificación DEBERÁ usar esos mismos bytes.
  Error DEBERÁ dejar salida vacía, sin fallback ni selección de perfil remoto.
- **LM03:** CUANDO decodifique LM v1, DEBERÁ exigir versión/magia exactas, 1–8 raíces
  absolutas distintas, 1–256 archivos ordenados por clave lógica única, raíz válida
  por archivo, todas las raíces utilizadas e índice principal existente. Nombres
  DEBERÁN excluir controles, traversal, componentes vacíos y enlaces simbólicos
  al abrir; tamaños/hashes DEBERÁN respetar el dominio bundle (256/512 MiB).
- **LM04:** CUANDO obtenga un archivo por clave, DEBERÁ usar exclusivamente su raíz
  y nombre fijados, descriptor retenido y hash completo. PID ajeno, cambio de
  archivo/raíz, clave desconocida o fallo DEBERÁN invalidar el proveedor.
- **LM05:** CUANDO componga PT v2, DEBERÁ fijar `application_evidence` al hash del
  manifiesto, comprobar nacimiento real/nonce/eventos/orígenes y usar las demás
  evidencias/UUID de LM. DEBERÁ mantener separadas las sesiones de arranque y
  salida; cada sesión DEBERÁ adquirir y revalidar al menos dos veces sin cambios.
- **LM06:** CUANDO valide en testconfig, DEBERÁ comprobar todos los archivos
  externos y medir preparación, primera muestra y revalidación, declarando el
  volumen de bytes releídos. Omisión de imagen cargada, digest incorrecto,
  ejecutable incorrecto y configuración manipulada DEBERÁN rechazarse.
- **LM07:** CUANDO publique costes, DEBERÁ distinguir mediciones de presupuestos
  productivos y mantener cerrada la captura. La plataforma macOS/dyld/Rosetta,
  AOT, datos transformados, peer y gates del emulador SHALL NOT darse por verificados.

## Diseño

`LaunchManifest` contiene raíces, archivos, índice principal, UUID y evidencias.
`decode_launch_manifest` valida un buffer acotado sin I/O; `read_launch_manifest`
lo adquiere y autentica por hash con puertos de identidad/bytes/digest. El SHA es
una expectativa del lanzador confiable, no una firma ni autenticación de un peer.
`launch_expected_files` produce claves `N/nombre` para `ManifestGuard`.
`MacOSLaunchFiles` compone un `MacOSArtifactFiles` por raíz, conserva el PID y
traduce únicamente claves exactas. No cambia los verificadores anteriores.

Formato binario canónico little endian, sin padding: magia de 8 bytes `SH3LM001`,
u32 cantidad de raíces, u32 cantidad de archivos, u32 índice principal,
UUID de 16 bytes, SHA de política de 32 bytes y SHA de plataforma de 32 bytes.
Luego cada raíz: u32 longitud y bytes ASCII (máximo 1025, mínimo 2). Luego cada
archivo: u32 raíz, u32 longitud de nombre (1–1022), u64 tamaño, SHA de 32 bytes y
nombre ASCII. No admite bytes finales. Claves ordenadas ascendentemente; las
raíces conservan orden explícito. Evidencias/UUID/hashes no pueden ser cero.

El harness privado recibe ruta/hash LM mediante entorno proporcionado únicamente
por su lanzador; lee y copia la configuración una vez por sesión. No se añade un
comando productivo. Una sesión nueva al salir es explícita: no reinicia un guard
fallido dentro de la misma sesión. La identidad obtenida cubre archivos completos
y sus cabeceras, no el contenido completo de memoria ni exclusión ABA.

## Tareas y aceptación

- [x] **LM-T1 / LM01–04:** formato/parser/adquisición y proveedor por raíces;
  tests de límites, bytes parciales, identidad, sustitución, symlinks, PID/fork.
- [x] **LM-T2 / LM05–06:** lanzar nueva copia testconfig con manifiesto previo;
  componer PT v2 completo, tres muestras por sesión y negativos reales.
  Verificar 200 archivos del candidato antes/después y conservar cada intento.
- [x] **LM-T3 / LM06–07:** cuatro modos, sanitizadores, cobertura, negativos,
  costes y auditoría reproducible. Umbrales de ejecución diagnóstica: reserva y
  piso 10 GiB, etapa 512 MiB, build 120 s, configure 45 s, prueba/sonda 60 s e
  individual 15 s. Son límites de laboratorio; no habilitan el coordinador.
