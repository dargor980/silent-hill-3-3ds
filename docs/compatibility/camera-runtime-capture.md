# Protocolo privado de observación de cámara europea

F02.07 · 2026-10-17 · [contrato CO01-CO08](../../schemas/camera-observation-v1.md).
La [captura completada](../execution/f02-07-camera-runtime-capture.md) registra nueve
eventos de tres invocaciones completas y dos recibos idénticos `validated_observations`.
A copia GPR6 a GPR4 en el slot y modifica GPR4 antes de retornar; las dos llamadas de B
conservan GPR16 en la invocación observada. La relación con recursos sigue pendiente.
La [primera tentativa](../execution/f02-07-camera-runtime-attempt.md) conserva su
resultado histórico sin eventos; el teclado físico permitió iniciar la sesión posterior.
Los sitios A/B del análisis son posiciones candidatas del ejecutable, no salas.

## Entorno instalado y comprobación de arranque

PCSX2 oficial **v2.8.2** está instalado en
`/Users/germancontreras/Applications/PCSX2-v2.8.2.app`.
El acceso `/Users/germancontreras/Applications/PCSX2 SH3.command` inicia ese binario
con `-datapath /Users/germancontreras/sh3-private-data/pcsx2` y `umask 077`.
En esta versión macOS, PCSX2 agrega `PCSX2` al directorio indicado: los datos efectivos
quedan en `/Users/germancontreras/sh3-private-data/pcsx2/PCSX2`.
Usar este acceso para conservar el perfil de investigación; abrir directamente el
bundle utiliza el perfil predeterminado de Application Support.

Se guardaron la carpeta de juegos `binaries`, controles de teclado predeterminados,
resolución nativa, arranque pausado y opciones avanzadas visibles. Parches generales,
cheats, widescreen y no-interlacing están desactivados para esta investigación.
La búsqueda automática de actualizaciones al iniciar queda desactivada para conservar
la versión; una actualización requiere una nueva identidad de sesión. El acceso
no inicia automáticamente la ISO. El usuario confirmó Nueva partida tras solicitar textos españoles y dificultad
Normal/Normal; no se verificaron esos ajustes mediante un lector de memoria del juego.

El perfil final acepta `-testconfig` (salida 0). La BIOS principal
`SCPH-70004_BIOS_V12_PAL_200.BIN` aportada por el usuario está copiada y seleccionada:
4.194.304 bytes, SHA-256
`d6653f4e93be2f6f9e9d690a934f26cf0f6ad4e348b69f41ef736732c3a6685b`.
Se conserva junto al ROM2 en
`/Users/germancontreras/sh3-private-data/pcsx2/PCSX2/bios`, sin modificar los originales.
PCSX2 la reconoce como Europa v2.00 (2004-06-14); la configuración inicial está completada.

Se probaron BIOS y arranque rápido de la ISO durante 20 y 25 segundos, respectivamente,
con cierre controlado y salida 0. Los logs identifican el ejecutable europeo e
inicializan Metal. En esa comprobación histórica no se verificaron pantalla, audio,
controles o breakpoints.
[Resultado y límites](../execution/f02-07-ps2-boot.md).
El INI de aquella comprobación, con arranque pausado restaurado, tenía SHA-256
`374aab2aee57025debfbba90ab3c8c71cf4230583f79c227e9da7579774b5c06`.
Reanudar al empezar una sesión. GameDB aplica ajustes automáticos descritos en la
evidencia; conservar versión y configuración al capturar. BIOS, memoria, logs y
savestates permanecen fuera del checkout.

Después de la primera tentativa de captura, el INI histórico tenía SHA-256
`a68611f865abaaf5326ed8742ef3e741bbde5b930a11f01aae98c4f7428b27fc`.
PINE y la carpeta de guardados quedaron restaurados; MTVU vuelve al valor previo.
Para exportar nuevos estados, desactivar MTVU antes de fijar otra sesión y comprobar
el perfil guardado. El hash completo verificado se conserva en el informe enlazado.

La sesión con nueve eventos ya está cerrada. Conserva estados privados y el INI de
captura por separado; el perfil restaurado tiene SHA-256
`124b133bc8cfab8c83c2878e447d1e3a892b79a39f4e2e2ce9457ef99140cb2d`.
PINE está desactivado, MTVU/carpeta de estados restaurados y `-testconfig` termina en 0.

## Preparar una sesión

1. Fijar la ISO/perfil europeos y todas las entradas de la cadena por SHA-256. Los
   argumentos reales de generación están en
   `build/f02-07-camera-observation/real-execution.json`. El comando es
   `python -m tools.inspectors.camera_observation plan`; `--help` describe todas las
   entradas obligatorias. Usar una salida nueva, nunca sobrescribir evidencia.
2. Usar `reports/local/f02-07-camera-observation-plan-v1.json`, SHA-256
   `55285f27e8dc2c9c894e1d07c9882f10091ef094a26e509a28d0cead89bfdd6b`,
   o regenerar un plan y fijar su nueva identidad. El plan actual contiene tres
   fronteras, nueve puntos principales, dieciséis checkpoints opcionales y seis
   rangos de código. Ningún punto está marcado como ejecutado.
3. Crear un directorio nuevo por sesión dentro de la raíz privada externa,
   modo 0700. Usar una sesión aleatoria de 32 caracteres hexadecimales minúsculos.
   Mantener archivos regulares 0600, sin symlinks ni hardlinks.
4. Registrar versión y hash del ejecutable host, BIOS e INI; CPU `EE`, método
   `manual-debugger-v1`. Calcular `environment_sha256` sobre JSON canónico:
   UTF-8, claves ordenadas, `ensure_ascii=False`, separadores `,` y `:`, sin espacios ni salto final.
   El hash del archivo `capture.json` se calcula sobre sus bytes completos.
   Los hashes del entorno son declaraciones del operador; el validador no inspecciona
   esos tres archivos ni autentica que los eventos provengan del emulador.
5. Abrir el depurador desde las opciones avanzadas, seleccionar el entorno R5900/EE
   y colocar los puntos del plan. La [documentación oficial del depurador](https://pcsx2.net/docs/advanced/debugger/)
   es la referencia de interfaz. Antes de capturar, comprobar que el código en memoria
   corresponde a los rangos/hash previstos. Una discrepancia detiene esa sesión;
   no se modifica el plan para aceptar una versión desconocida.

## Registrar la observación

Para cada frontera usar una sola invocación: antes de la llamada → entrada después
del delay slot → checkpoints opcionales → continuación al retornar. No mezclar
invocaciones, sesiones, recargas de savestate o ejecuciones distintas. Capturar los
32 bits bajos de **todos y solo** los GPR pedidos por cada punto, con ocho dígitos
hexadecimales minúsculos. PC y secuencia deben coincidir con el contrato.

En A interesa comparar GPR6 anterior con GPR4 de entrada. En B interesa comparar
GPR16 al entrar y al retornar. GPR31 de entrada debe coincidir con la continuación
JAL del plan. Si se detiene la sesión después de entrar sin observar retorno, marcar
`incomplete`; no convertirla en `not_reached`. Este último estado solo declara que
esa frontera no se observó durante la sesión, sin concluir que sea inalcanzable.

Guardar cada snapshot de código utilizado como `<sha256>.bin`, tamaño/hash exactos
según el plan. Las muestras de datos son opcionales: como máximo 16, de 1 a 4096
bytes cada una, empezando en el valor de un GPR capturado y sin desbordar 32 bits.
No asumir que el dato pertenece al catálogo. Archivos binarios y valores de registros
permanecen en la carpeta de sesión, sin imprimirlos en terminales o reportes públicos.

La exportación a savestate puede asistir la lectura mediante el [contrato PS01–PS07](../../schemas/pcsx2-state-reader-v1.md).
Exigir hash esperado y archivo privado estable, comprobar PC/no-delay-slot, seleccionar
solo los registros del punto y mantener su vínculo con la secuencia operada en el
depurador. El lector no acredita pausa, sesión ni orden por sí mismo. En v2.8.2,
Paso a paso desde JAL alcanzó la entrada después del slot y Salir de función alcanzó
el retorno; comprobar cada PC antes de atribuir un evento, sin asumir ese resultado.

Construir `capture.json` con los campos exactos del contrato. La lista de snapshots
debe cubrir exactamente los rangos usados por eventos; una captura sin eventos
declara todas las fronteras `not_reached`. JSON máximo 1 MiB, 128 eventos, 32 rangos
de código; los checkpoints fuera de ventana que el plan difiere no son puntos válidos.

## Validación y conclusión permitida

Ejecutar `python -m tools.inspectors.camera_observation validate` con los mismos
argumentos y hashes de entrada del plan, además de `--plan`, `--plan-sha256`,
`--private-root`, `--capture-sha256` y una ruta `--output` nueva bajo `reports/local`.
La validación regenera la cadena desde la ISO, compara el plan completo, verifica
archivos/eventos y publica el recibo solo después del cierre estable. Ejecutar la
publicación de recibos antes del chequeo de custodia del repositorio; no solaparlos.

El recibo contiene conteos, hashes y comparaciones; no valores GPR, direcciones de
datos ni bytes. Un resultado `validated_observations` acredita coherencia de la
evidencia aportada. `validated_no_observations` no acredita haber observado esos
puntos. Ninguno autentica ejecución, demuestra preservación universal o identifica
un recurso de cámara.

Después deberá demostrarse la cadena entre el puntero observado y un ID/rango/hash
del catálogo. Solo esa evidencia permitirá proponer un contrato para campos 92/108,
colas o dependencias; F02.07/Q05/G02 siguen abiertos.

## Continuación sobre los estados conservados

La [búsqueda exacta](../execution/f02-07-camera-resource-link.md) ya comparó diez
muestras con ambas extracciones. Encontró seis hits en un único candidato de 1.536
bytes: prefijo de 256 bytes en A y de 64 bytes en B. No reabrió PCSX2 ni alteró la
captura. La siguiente subtarea conserva `camera-resource-link-eu/origin` pendiente
para comprobar mapeo y carga/escritura, antes de atribuir semántica al recurso.


La [observación posterior SRC28](../execution/f02-07-camera-writer.md) usa una sesión
independiente restaurada desde entrada A. Conserva siete estados y dos pares
coherentes, uno sin cambio y otro BEQ+SW que modifica tres bytes. Se cerró como
parcial, sin retorno ni prueba de traducción. No añade eventos a esta captura histórica.


[SRC29](../execution/f02-07-camera-return.md) repite el par de SRC28 en otra sesión
y captura el retorno completo, igual al retorno histórico en los 1.536 bytes.
La sesión histórica conserva sus nueve eventos; mapa y carga siguen pendientes.

[SRC30](../execution/f02-07-effective-mapping.md) define MP01–MP08 y valida mapas
suministrados con fixtures propios. El sondeo del PCSX2 oficial, en otro perfil
y sin cargar el juego, recibió EPERM al solicitar puerto host de lectura.
La captura del mapa efectivo requiere instrumentación en un build separado;
este resultado no cambia los eventos ni la hipótesis física históricos.
