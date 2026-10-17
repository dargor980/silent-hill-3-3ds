# F02.07 — Primera comprobación de cámara en ejecución

2026-10-17 · avance parcial de `camera-runtime-capture-eu` · CO01–CO08.

El depurador EE carga los nueve puntos principales y la memoria de PCSX2 coincide
con los **seis rangos/hash del plan**. El juego llega visualmente al aviso de tarjeta
de memoria sin formatear. **No se observó ninguna de las tres fronteras A/B.**
Dos recibos idénticos registran `validated_no_observations`; F02.07/Q05/G02 siguen
abiertos. [Metadatos y procedencia](../compatibility/camera-runtime-attempt-evidence.json).

## Evidencia obtenida

- PCSX2 oficial v2.8.2, ISO europea y BIOS ya identificadas; misma cadena de entradas
  del plan `55285f27e8dc2c9c894e1d07c9882f10091ef094a26e509a28d0cead89bfdd6b`.
- Nueve breakpoints de ejecución configurados: antes/entrada/retorno por frontera.
  Solo los tres anteriores a la llamada estaban activos. Las entradas conservan
  una condición sobre el retorno previsto. Carga de las nueve filas comprobada en UI.
- Pausa automática en la entrada del ELF. PINE informó versión v2.8.2 y estado
  pausado; se leyeron seis ventanas mediante `Read32`, comprobando pausa antes y
  después. Los seis SHA-256 coinciden con el plan. Esto comprueba código cargado,
  no que se ejecuten esos sitios.
- Dos estados privados, sin sobrescritura: control en la entrada del ELF y pausa
  ante el aviso de tarjeta. Ambos ZIP pasan CRC y declaran versión de estado
  `0x9A590000`/v2.8.2. La lectura exploratoria del control coincide con la entrada
  esperada. No se importaron sus GPR como eventos ni se creó un parser de producción.
- Arranque visual de SH3 observado mediante la interfaz: aviso en inglés de tarjeta
  sin formatear, selección «No». No se confirmó formateo. Español, Normal/Normal,
  sonido, respuesta del mando y partida jugable quedan sin verificar.

PINE apoyó la comprobación de memoria/exportación. Se usó un socket Unix bajo carpeta
0700, con `umask 077`, sin TCP. MTVU se desactivó para esta sesión por la advertencia
de PCSX2 sobre estados guardados. No se escribieron registros, memoria, PC ni
instrucciones del juego. Las fuentes oficiales v2.8.2 consultadas están fijadas por
URL/hash en la evidencia. Son referencias GPL-3.0+; sus archivos no se incorporaron
al repositorio. No se declara implementación clean room.

## Límite de la prueba y recibos

Los controles de accesibilidad permiten ejecutar/pausar y accionar menús de PCSX2.
Después de cerrar el depurador hubo que volver a obtener la aplicación para recuperar
el menú principal. Las teclas enviadas no produjeron una respuesta observable del
juego; los clics por coordenadas fallaron con `noWindowsAvailable`. Esto bloqueó el
avance desde el aviso. No demuestra un defecto del juego ni de los controles físicos.

Las dos sesiones preparatorias tampoco produjeron eventos y se cerraron antes de
la sesión final. Sus estados no se mezclaron. La sesión final terminó sin haber
entrado en ninguna invocación A/B: las tres fronteras se declaran `not_reached`.
`complete` en el JSON indica cierre del registro de esta tentativa, no cumplimiento
de F02.07 ni una captura de cámara satisfactoria.

Se ejecutó dos veces el CLI existente `camera_observation validate`, que vuelve a
verificar la ISO y la cadena de entradas. Los recibos tienen **1.375 bytes**, SHA-256
`c2a89c0df879e1078c11d4422f81df7b7fe181ed27364b8810ee3110dd5c5d88`.
Declaran cero eventos, cero snapshots asociados a eventos y cero muestras de datos;
`execution_authentication` permanece `not_provided`. La comprobación separada de
seis rangos no se inserta como si proviniera de eventos inexistentes.

Comandos, tiempos y metadatos sanitizados: `build/f02-07-camera-runtime`.
Recibos: `reports/local/f02-07-camera-runtime-attempt-v1{,-repeat}.json`.
Los estados, logs, INI y bytes permanecen exclusivamente en
`/Users/germancontreras/sh3-private-data/f02-07/capture-e4f01a42cbcf4b0db3e6e2400e0821dd`,
con directorio 0700 y archivos 0600. Los registros anteriores se conservan.

## Cierre y validación

Se solicitó SIGTERM y se comprobó que el proceso salió; al ser un proceso separado
no se atribuye un código de salida que no se recogió. El socket desapareció. PINE,
MTVU y el directorio de estados se restauraron a sus valores previos. El acceso
habitual sigue usando el perfil privado y arranque pausado. `-testconfig` posterior
terminó con código 0; INI final SHA-256
`a68611f865abaaf5326ed8742ef3e741bbde5b930a11f01aae98c4f7428b27fc`.

Las **128 pruebas de `test_camera_observation.py` pasan**. No se modificaron código
Python/C++, contratos del validador, SDK ni pipelines; no se repitió el build 3DS
ni se atribuye a esta tentativa la batería histórica completa de 1435 pruebas.
Las comprobaciones de arquitectura, custodia, trazabilidad EARS y enlaces pasan
con cero errores. Se verificaron permisos y hashes finales; el log de `-testconfig`
se restringió a 0600 antes del cierre de la comprobación de custodia privada.

## Continuación concreta

1. Resolver la entrada de controles: iniciar desde `Applications/PCSX2 SH3.command`,
   abrir la ISO, reanudar desde Sistema y comprobar físicamente que K confirma «No»
   en el aviso. Si tampoco responde, revisar Pad1/Keyboard y foco de la ventana.
   No dar por verificado el mando hasta observar una transición del menú.
2. Seleccionar español y Normal/Normal, registrar ese contexto y comenzar una sesión
   nueva con identidad de entorno fijada. Una recarga de estado no continúa una
   invocación de la sesión anterior. Si se exportan estados, desactivar MTVU antes
   de iniciar esa sesión y conservar la configuración correspondiente.
3. Revalidar los seis rangos, detener una invocación antes/entrada/retorno por
   frontera y capturar los GPR exactos del plan. Si se automatiza la importación
   de estados, primero especificar y probar un lector acotado para esta versión;
   la lectura exploratoria del control no basta para aceptar registros arbitrarios.
4. Repetir validación del registro con eventos y solo después investigar el vínculo
   puntero → ID/rango/hash del catálogo. Campos 92/108, colas y salas siguen pendientes.
