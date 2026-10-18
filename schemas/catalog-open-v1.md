# Selección de catálogo y apertura — CA01–CA09

Unidad LP-C posterior a [DA01–DA09](descriptor-acquisition-v1.md). El adaptador
concilia evidencia suministrada de selección/apertura; no autentica ejecución
ni identifica todavía el objeto del driver que efectúa la lectura.

Estado: implementado y probado con fixtures propios; [SRC58](../docs/execution/f02-07-catalog-open.md)
registra investigación, resultados y siguientes tareas. Captura real pendiente.

## Requisitos EARS

- **CA01:** CUANDO se investigue el resolver, DEBERÁ fijar el directorio, fila,
  referencias a cadenas y rutas de resolución/llamada mediante ELF, estado y
  catálogo privado. Un registro en un estado posterior SHALL NOT acreditar
  que la ejecución lo seleccionó. DEBERÁ distinguir archivo empaquetado de
  rutas alternativas y conservar desconocidos.
- **CA02:** CUANDO se suministre el origen, DEBERÁ validar hashes de catálogo,
  contenedor y recurso, ruta ISO ASCII canónica, nombre acotado y rango positivo
  dentro del contenedor. El adaptador puro SHALL NOT afirmar que releyó esos
  originales; el ejecutor deberá fijarlos mediante los lectores existentes.
- **CA03:** CUANDO concilie selección, DEBERÁ comprobar mapa/estado del código,
  configuración, cabecera, fila y cadenas. DEBERÁ derivar la pertenencia de la
  fila al directorio y de las cadenas a su área, y exigir que el registro CPU
  seleccionado apunte a esa fila. Prefijo, nombre, solicitud y rango DEBERÁN
  coincidir con el origen suministrado. Un rango aislado SHALL NOT bastar.
- **CA04:** CUANDO acepte la ruta empaquetada soportada, DEBERÁ exigir prefijo
  `cdrom0:/`, un separador terminal de contenedor y un nombre sin separadores.
  La ruta ISO se comparará en mayúsculas ASCII conforme al driver investigado;
  la solicitud y la ruta resuelta DEBERÁN conservar los bytes observados. No
  deberá normalizar rutas arbitrarias, traversal, controles o otras variantes.
- **CA05:** CUANDO concilie las cuatro pausas, DEBERÁ exigir identidad común,
  secuencias regionales consecutivas, slots distintos y ciclos crecientes
  dentro de LP. Código, configuración, mapas compartidos, ruta y rango DEBERÁN
  conservarse donde corresponda; PC, marco, punteros, flags y modo DEBERÁN
  ajustarse al perfil privado fijado, incluido el delay slot de apertura.
- **CA06:** CUANDO vincule apertura y descriptor, DEBERÁ exigir fila reservada
  durante llamada/retorno, retorno no negativo y fila final abierta con ese
  resultado, generación incrementada una vez, token consistente y rango
  exacto. Cierre, error, generación reciclada o wrap DEBERÁN rechazarse.
- **CA07:** CUANDO produzca un resultado, DEBERÁ informar únicamente hashes,
  tamaños y conteos; SHALL NOT publicar cadenas, registros ni direcciones.
  DEBERÁ distinguir consistencia suministrada, código comparado, identidad del
  driver pendiente y autenticación no provista. SHALL NOT generar eventos Read.
- **CA08:** CUANDO se pruebe la unidad, DEBERÁ incluir catálogos ajenos, igual
  rango en otro contenedor, nombres parecidos, apertura fallida, fila residual,
  reciclado, cambio de mapas/código, identidad y límites de secuencia/ciclos.
  DEBERÁ pasar regresión y gates ≥80 % de líneas/ramas sin originales en CI.
- **CA09:** ANTES de capturar en PCSX2, DEBERÁ completar la identificación del
  driver, posición y ruta de lectura/caché, planificar ≤48 estados y ≤256
  solicitudes regionales/hits con los demás límites LP, y partir antes de la
  carga. Restaurar el estado posterior SHALL NOT sustituir esa observación.

## Diseño

`catalog_open` es un adaptador puro. Recibe un origen suministrado, perfil de
código privado y cuatro conjuntos LF; reutiliza `validate_pause` e
`inspect_descriptor`. Canal, guardia, lectura ISO/MFA y publicación permanecen
en adaptadores separados. El perfil contiene ventanas verificadas por el
ejecutor; se compara el código y se decodifica JAL/delay slot, sin interpretar
todo el cuerpo ni autenticarlo con un perfil arbitrario.

Las pausas tienen 7, 5, 5 y 5 rangos: 22 solicitudes y cuatro estados. En la
selección se capturan código, configuración, cabecera, fila, prefijo, nombre
y solicitud. Las otras pausas capturan código del wrapper, configuración,
descriptor, ruta resuelta y rango. El marco soportado y registros corresponden
al ABI investigado; una variante exige contrato/evidencia nuevos.

## Tareas y aceptación

1. Fijar resolver, transformaciones, entrada candidata y llamada; repetir el
   análisis con informe idéntico y conservar el plan privado sin sobrescribir.
2. Implementar el adaptador y pruebas independientes; pasar quality y cobertura.
3. Vincular después objeto del driver, posición y lectura/caché; solo entonces
   planificar LP-D y la conversión a eventos de procedencia.
