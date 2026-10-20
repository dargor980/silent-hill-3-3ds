# F02.07 — Frontend, espera circular y enlace completo (SRC84)

Fecha: 2026-10-18. Continúa IW-FRONT bajo [WF01–WF08](../../schemas/worker-frontend-v1.md).
El frontend completo compila/enlaza y el candidato pasa testconfig con un perfil
aislado. Las pruebas entre hilos confirman una espera circular recuperable por
plazo: esa recuperación no garantiza disponibilidad de UI y mantiene abierta la
cancelación prioritaria. No se ha ejecutado una VM ni una captura nueva del juego.

## Rutas actuales

Se fijan 75 referencias léxicas en cuatro archivos, más los siete usos de
BlockingQueuedConnection encontrados en todos los .cpp de pcsx2-qt. Esto es un
inventario de rutas, no una prueba de ausencia universal de productores/locks.

| Ruta | Observación sobre la fuente actual | Consecuencia |
|---|---|---|
| Translations.cpp, InstallTranslator | LocaleChanged ya pasa por RunOnCPUThread; no sigue siendo un productor UI→GS directo | Preservar la serialización integrada anteriormente |
| QtHost.cpp, RunOnCPUThread/runOnCPUThread | Entrega encolada o bloqueante; slot cancela antes de func | Un retorno bloqueante debe conservar su contrato |
| QtHost.cpp, closeInputSources | Desde otro hilo invoca reloadInputDevices con BlockingQueuedConnection | Ruta bloqueante adicional; se conserva ese comportamiento previo, sin corregirlo incidentalmente |
| MainWindow.cpp, conexiones de ventana | Acquire/ReleaseRenderWindow usan BlockingQueuedConnection desde GS hacia UI | UI debe poder atender mientras GS drena o cierra |
| QtHost.cpp, RunOnUIThread/GetTopLevelWindowInfo/CancelGameListRefresh | Entran al hilo UI; pueden esperar según la ruta | Inventariar llamadores y locks; no extrapolar del slot |
| MainWindow.cpp, pauseAndLockVM | Solicita pausa; fuera de Apple puede bombear eventos al salir de fullscreen | No confundir VMLock con un mutex que excluya todos los escritores |

## Pruebas entre hilos

Los tres escenarios de la [fixture](../../tests/fixtures/pcsx2-worker-frontend/README.md)
pasan en normal, ASan/UBSan y TSan: nueve ejecuciones finales. Usan QThread/QObject
y despacho QtCore real, cuatro cuerpos adicionales y los dos bucles VU/GS de
SRC83. Los receptores de ventana, renderer, VU y servidor PINE siguen siendo dobles.

Con UI disponible, GS completa su petición síncrona y el drenaje termina. Un
callback CPU encolado conserva su payload y se entrega una vez después del retiro.
En el caso circular, UI espera CPU mientras GS espera UI; CPU vence el plazo de
200 ms, retira las retenciones y ambos callbacks terminan. Las muestras finales
de bloqueo UI rondan 201 ms. La API admite plazos mayores; esta prueba no convierte
esa espera en aceptable para interacción ni acredita una garantía de latencia.

Dos mutantes fallan como se esperaba: convertir el retorno síncrono en asíncrono
y ejecutar dos veces el callback. Los grupos de procesos quedan limpios.

TSan inicialmente señaló la publicación del primer callback a través del QtCore
sin instrumentar. Se preservó el resultado y se compiló QtCore 6.11.1 con TSan,
incluyendo Objective-C++ de Darwin. Los 256 comandos del target Core incorporan
el flag; Bootstrap se trata por separado. Las nueve ejecuciones finales no
presentan avisos. Una ejecución adicional con diagnóstico dyld confirma que se
carga la biblioteca instrumentada. No se usaron supresiones para obtener ese resultado.

La fuente Qt se compara con 22.859 archivos originales y el diff fijado anterior.
No se reinstala sobre el prefijo productivo. Se conserva la política específica
de Qt Base: inicio 18 GiB, piso 12 GiB, etapa 4 GiB y dos jobs. El primer configure
no instrumentaba los archivos Objective-C++; se conservó y reemplazó por una etapa
nueva con el flag explícito antes de compilar Core.

## Enlace y smoke test

El primer build completo encontró `try` con excepciones deshabilitadas en
cooperative_gate.cpp. Esa frontera captura bad_alloc para rechazar una reserva
fallida. Se creó una copia privada nueva que cambia únicamente CMake para añadir
`-fexceptions` a ese archivo. Los demás comandos conservan sus flags anteriores.
Se preservan diecinueve copias de PCSX2 y ambos árboles de build.

El segundo build completo pasa: 824 entradas, trece fuentes propias, x86_64,
Release y configuración fijada. Inicio con reserva IB02 de 20 GiB, piso 10 GiB,
etapa máxima 8 GiB, dos jobs; duración observada 402,198 s. Se compilan los tests
originales y ambos programas CTest pasan, 113 tests internos en total.

Se crea un candidato separado con 200 archivos y 42 Mach-O x86_64. Se verifican
rutas de carga y firma ad hoc; el bundle original del build y la aplicación
instalada se conservan. `-testconfig` pasa con un perfil privado nuevo, sin pedir
la ISO. Este arranque de configuración no acredita ejecución de la VM, las
guardias bajo gameplay ni el rendimiento del port Nintendo.

La medición LLVM adicional del núcleo WorkerDrain obtiene 100 % de líneas y
85,53 % de ramas. Los 154 CTest por preset de SRC83 no se repiten: el núcleo y
sus tests no cambian en esta unidad. CI remoto y build Nintendo no se ejecutan.

## Continuación necesaria

IW-FRONT1 y la preparación/enlace IW-FRONT3 quedan comprobados en este alcance.
IW-FRONT2 acredita entrega y recuperación, pero sigue parcial respecto de UI
disponible. La siguiente unidad debe anunciar las llamadas externas bloqueantes
al propietario CPU y retirar el intento antes de despachar su callback, sin
cambiar el retorno síncrono, perder operaciones ni liberar workers desde UI.

Los hechos de admisión GS/VU, RDebug y otros escritores siguen desconocidos en
SampleObserverAdmissionProfile. Se mantiene admisión vacía y captura global sin
habilitar. F02.07, B3-C/B4, CQ3-C/D, CQ-4 y AD-3 permanecen abiertos.
