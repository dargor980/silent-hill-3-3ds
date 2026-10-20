# F02.07 — Cancelación ante esperas externas (SRC85)

Fecha: 2026-10-18. Continúa IW-UIWAIT con [EW01–EW09](../../schemas/external-waits-v1.md).
CPU cancela el intento de observación cuando otro hilo anuncia que va a esperarlo,
retira GS→VU→PINE y después despacha el callback. La llamada bloqueante conserva
sus datos y su retorno. El anuncio dura hasta que termina esa llamada y evita
admitir otro intento durante ese intervalo.

## Implementación y responsabilidades

ExternalWaits cuenta scopes con atomics y RAII; no conoce Qt, callbacks ni tokens
VU/GS. Cada scope retira solamente su reserva. Si se agota capacidad o no puede
registrarse tras 32 CAS, conserva un rechazo permanente, sin envolver el contador.
CPU es el único propietario que cancela y libera retenciones.

La copia privada nueva integra la señal en RunOnCPUThread bloqueante externo y
en la conexión directa de closeInputSources. Esta última sigue invocando
reloadInputDevices, comportamiento previo que no se modifica incidentalmente.
Las llamadas asíncronas y la ejecución inline en CPU no anuncian espera.
Queue rechaza mientras hay anuncio; Poll y BeforeObserverProducer cancelan el
intento existente, también durante PINE antes de iniciar retenciones de workers.

No cambia el perfil de admisión: GS/VU, RDebug y otros escritores siguen sin
acreditación global. Un callback puede tener sus propios locks o esperas; esta
señal elimina la retención del observador como causa de demora, sin demostrar que
toda operación del proveedor sea no bloqueante.

## Pruebas

La [fixture](../../tests/fixtures/pcsx2-external-waits/README.md) ejecuta ocho casos
con QThread/QObject, QtCore real y los bucles exactos VU/GS: 24 ejecuciones finales
en normal, ASan/UBSan y TSan. El QtCore instrumentado de SRC84 se reutiliza intacto;
dyld confirma que se carga y no se aplican supresiones.

Los ciclos UI→CPU/GS→UI cancelan antes del deadline de 2 s. En las seis muestras
finales con ambos tokens aceptados, UI espera entre 1,095 y 1,488 ms. Son medidas
locales sujetas al planificador, no una garantía de latencia. También se comprueba
cancelación antes de solicitar GS, durante PINE por ambos puntos de entrada,
retorno inline, payload, entrega única y reanudación de intentos tras la espera.

Cinco controles negativos fallan con aserciones específicas y procesos cerrados:
aviso ausente, retiro prematuro, ruta directa sin aviso, cancelación PINE omitida
y borrado de todas las reservas al retirar una sola. La primera fixture exigía un
token GS ya solicitado cuando todavía podía no existir; se conserva el fallo y
se separan ambas intercalaciones. El primer mutante PINE no sustituyó su include
por precedencia de búsqueda; se conserva como control no efectivo. La versión
final resuelve el fragmento alterado y detecta el fallo.

Los seis tests del núcleo pasan con TSan; la regresión aprueba 160 CTest por
preset Debug/Release/ASan-UBSan, 480 ejecuciones. LLVM mide 100 % de líneas y
87,5 % de ramas de external_waits.cpp. Se compilan ocho objetos reales ON/OFF,
incluido moc QtHost. Los tests públicos entran en los presets y CI existentes.
No se ejecutan CI remoto, suite Python completa ni build Nintendo en esta unidad.

## Enlace, custodia y límites

La configuración completa contiene 825 entradas y catorce fuentes propias.
Conserva -fexceptions únicamente en cooperative_gate.cpp. El build usa etapa
nueva, dos jobs, reserva inicial IB02 de 20 GiB, piso 10 GiB y máximo de etapa
8 GiB. La reserva se revalidó antes de iniciar; no se cambió el umbral.

El build completa en 310,839 s. Pasan dos programas CTest, 113 tests internos,
y testconfig del candidato privado con 200 archivos y 42 Mach-O x86_64.
El posprocesado original informa componentes sin firma; se conserva ese bundle
y se corrigen ID/rutas/firmas únicamente en el candidato, cuya firma ad hoc se
verifica de forma independiente. Se conserva la aplicación instalada, el bundle del build y
el candidato previo. Este smoke de configuración no inicia la ISO ni acredita
VM, widgets completos bajo carga o rendimiento Nintendo.

Se verifican veinte copias privadas de PCSX2 y los historiales SRC83/84. El
CMake público evoluciona para añadir seis tests; su versión SRC83 se conserva en
un snapshot con el hash anterior. Los informes previos no se reescriben ni se
presentan como una repetición contra un CMake que ya cambió. La auditoría nueva
comprueba explícitamente ese snapshot, las demás entradas, fuentes y recibos.

IW-UIWAIT1–3 e IW-FRONT2 quedan comprobados en este alcance. B3-C/B4,
B3-B3c/CQ3-C, CQ3-D/CQ-4 y AD-3 siguen abiertos para llamadores/locks, servidor
PINE conjunto y VM. La siguiente unidad IW-CALLERS debe clasificar las esperas
bloqueantes reales y sus dependencias antes de extrapolar la fixture de callbacks
simples. F02.07 sigue abierta y no se añade una captura del juego.
