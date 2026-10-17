# F02.07 — Captura de tres fronteras de cámara europeas

2026-10-17 · `camera-runtime-capture-eu` · CO01–CO08 / PS01–PS07.

**Resultado:** nueve eventos de tres invocaciones completas, seis rangos de código
coincidentes antes y después, y dos recibos idénticos `validated_observations`.
Se cierra esta instancia de observación. F02.07/Q05/G02 permanecen abiertos:
todavía no hay un vínculo demostrado con un recurso del catálogo ni salas elegidas.

## Observaciones y alcance

| Frontera del plan | Secuencia | Resultado de los 32 bits bajos |
|---|---|---|
| A / `0c1a0b8c…` | antes → entrada → retorno | GPR6 previo = GPR4 de entrada; GPR4 de entrada ≠ GPR4 al retorno |
| B1 / `6b2adeb9…` | antes → entrada → retorno | GPR16 de entrada = GPR16 al retorno |
| B2 / `6a6d0aad…` | antes → entrada → retorno | GPR16 de entrada = GPR16 al retorno |

Los tres GPR31 de entrada coinciden con sus continuaciones JAL. Todos los PC
coinciden exactamente con el plan y ninguno de los nueve estados está dentro del
delay slot. No se capturaron checkpoints opcionales ni muestras de datos. Las
igualdades describen estas invocaciones; no garantizan conservación en otras ramas.
En particular, la búsqueda del origen de A debe partir del argumento de entrada,
no tratar su GPR4 de retorno como el mismo puntero.

Los nombres A/B designan sitios del ejecutable, no habitaciones. Esta evidencia no
identifica formato, campos 92/108, colas, recursos, dependencias ni gameplay 3DS.
El recibo comprueba coherencia e integridad, no autentica ejecución ni entorno.

## Sesión y procedimiento

Sesión `bdaad9edb3134b5fa876ae7ba60d0d99`, PCSX2 oficial v2.8.2, ejecutable x86_64
en macOS arm64, CPU EE. ISO europea SLES-51434 revisión 1.02 y BIOS propia Europa
v2.00 fijadas por hash. Identidades completas y metadatos sin registros en
[SRC25](../compatibility/camera-runtime-capture-evidence.json).

El usuario confirmó respuesta del teclado físico e inicio de Nueva partida tras
solicitar español y Normal/Normal. Esa es la evidencia del perfil elegido; no se
leyeron independientemente los ajustes del juego desde su memoria. La automatización
por coordenadas siguió siendo limitada; las acciones accesibles del depurador sí
permitieron ejecutar Paso a paso, Salir de función y Ejecutar.

1. Se creó un directorio privado y un socket Unix bajo padre 0700. PINE se activó
   solo para la sesión y MTVU se desactivó antes de iniciarla.
2. Se verificaron seis ventanas de código con lecturas PINE mientras EE estaba
   pausada. Se conservó un estado de control en la entrada del ELF, fuera de eventos CO.
3. Tras iniciar la partida se alcanzó el breakpoint anterior a la llamada de A.
   Se exportó el estado y se usaron Paso a paso y Salir de función para obtener
   entrada y retorno. Luego Ejecutar alcanzó B1 y B2, cada una observada por separado.
4. Se guardaron slots 2–10 sin sobrescribirlos. No hubo cargas de estado, reinicios
   ni invocaciones intercaladas entre los eventos. PINE confirmó pausa antes y después
   de cada exportación; su respuesta por sí sola solo acepta una solicitud asíncrona.
   Se esperó un archivo estable antes de comprobar hash, miembros y PC.
5. El lector probado importó únicamente registros pedidos por el plan. Se contrastó
   también el estado de control y se repitieron las seis ventanas en memoria al final.
   La versión final del lector reimportó los nueve estados con resultados idénticos.
6. El validador existente regeneró el plan desde la ISO y publicó dos recibos nuevos.
   PCSX2 se cerró desde su menú, preservando estados. Se restauraron exclusivamente
   PINE, MTVU y carpeta de savestates; desapareció el socket y `-testconfig` terminó en 0.

Raíz privada de esta sesión:
`/Users/germancontreras/sh3-private-data/f02-07/capture-bdaad9edb3134b5fa876ae7ba60d0d99`.
Contiene estados, registros, ventanas, configuraciones y logs; directorios 0700 y
archivos regulares 0600. Ninguno se publica en el repositorio ni en artefactos CI.
La partida queda preservada en los estados, con PCSX2 cerrado.

El INI de captura tiene SHA-256
`3aaa3070821c6c00e64ee4951d91a3e3e7538a57870681dcb95d980f2fa7917f`.
El INI restaurado tiene SHA-256
`124b133bc8cfab8c83c2878e447d1e3a892b79a39f4e2e2ce9457ef99140cb2d`.
Son momentos distintos; el segundo no sustituye la identidad del entorno capturado.

## Lector propio y SOLID

[Contrato EARS PS01–PS07](../../schemas/pcsx2-state-reader-v1.md).
`pcsx2_state.py` valida el contenedor acotado, decodifica el prefijo conocido y ofrece
selección explícita por PC/GPR. `state_files.py` es el adaptador de custodia POSIX:
raíz externa, no enlaces, permisos, SHA-256 y estabilidad hasta el cierre.
El contrato CO y su validador se reutilizan sin cambios.

El layout está fijado a v2.8.2 little-endian x86_64. Se consultaron los hechos del
formato en las fuentes oficiales ya registradas en SRC24; no se incorpora su código
ni se declara clean room. Se rechazan otros layouts, ZIP64, cifrado y campos extra.
El recorrido previo del directorio central comprueba el número real de entradas antes
de construir objetos ZIP. Solo se descomprimen versión y estructuras internas; RAM
y demás miembros quedan opacos. El lector no es un importador general de savestates.

Python local 3.14.6 admite la compresión Zstandard de estos estados. Los fixtures
propios usan stored/deflate, compatibles con Python 3.13 del pipeline. Un host sin
el método necesario recibe `STATE_COMPRESSION`; no se instalaron dependencias nuevas.

## Validación y reproducción

- Plan: SHA-256 `55285f27e8dc2c9c894e1d07c9882f10091ef094a26e509a28d0cead89bfdd6b`.
- Captura privada: SHA-256 `216003229ac966e9a6e0d1153be9c6a80ef7550ffc5c7d23ab52bb1c2cb34e49`.
- Recibos: `reports/local/f02-07-camera-runtime-capture-v1{,-repeat}.json`, 1.343 bytes
  cada uno, SHA-256 `6280e7b164c12805ecead3d3415fbe18588c726369553d6ea17d8b215d04898d`.
- Argumentos exactos, duración y salida: `build/f02-07-camera-runtime-native/validation.json`.
  Cada llamada `camera_observation validate` verifica nuevamente ISO, cadena y plan.
  La segunda valida el mismo material; no representa una segunda sesión del juego.
- Regresión final: **1.517 pruebas aprobadas**, incluidas 82 nuevas del lector y su
  integración con CO. Cobertura Python: **98.66 % de líneas / 97.43 % de ramas**;
  ambos módulos nuevos tienen 100 % de líneas y ramas. Gate independiente ≥80 % y
  Ruff check/format y arquitectura/custodia/specs aprobados. Reportes: `build/f02-07-camera-runtime-native/pytest-final.xml`
  y `coverage-final.json`.

La primera suite durante la publicación de recibos terminó con 1.511 aprobadas y
un fallo de custodia al observar un archivo temporal de publicación. Se conserva
esa incidencia: validación real y chequeo de custodia deben ejecutarse secuencialmente,
con el árbol estable. No se relajó la política de archivos para admitir la carrera.
El job `quality` existente descubre los tests nuevos automáticamente; CI remoto y
compilación 3DS no se ejecutaron en esta instancia de herramientas Python.

## Siguiente instancia

`F02.07/camera-resource-link-eu`: demostrar o descartar una relación concreta entre
el argumento de A / base de B y un ID, offset y SHA-256 del catálogo. Requiere un
contrato de muestreo acotado, fixtures propios y nueva evidencia de origen; igualdad
de registros no basta. La [tarea detallada](../specs/sh3-3ds/tasks/F02.md) fija
requisitos, experimentos, resultados negativos y criterio de aceptación.
