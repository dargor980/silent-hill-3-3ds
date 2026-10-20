# Esperas externas CPU/Qt — SRC85

Fixture propia para la copia privada `source-external-waits-v1`. No contiene
cuerpos de PCSX2. `joint_setup.inc` reutiliza el soporte propio SRC83 y resuelve
71 fragmentos exactos en el directorio privado. QThread, QObject, QtCore,
WorkSema y semáforo Mach son reales; renderer, ventana, efectos VU, InputManager,
servidor PINE y épocas host siguen siendo dobles.

| Caso | Invariante comprobada |
|---|---|
| gs_ui | GS puede completar su llamada síncrona a UI y el intento termina |
| queued | La llamada asíncrona no anuncia espera; payload y entrega única después del retiro |
| cycle | UI espera CPU mientras GS espera UI; la señal cancela antes del deadline |
| direct_cycle | La conexión bloqueante de closeInputSources conserva su destino anterior reloadInputDevices y su retorno |
| early_cycle | Cancelación antes de solicitar GS; no se exige un token nunca emitido |
| inline | RunOnCPUThread bloqueante desde CPU ejecuta inline, sin anunciar espera; closeInputSources mantiene su ruta local |
| pine_poll | Una espera durante el cierre PINE cancela por Poll antes de iniciar retenciones VU/GS |
| pine_before | BeforeObserverProducer cancela durante PINE antes del despacho |

Las rutas con anuncio verifican que impide nuevos intentos mientras vive. Todos
los casos comprueban que un intento posterior puede completar tras el retiro. Los ciclos usan un
plazo de 2 s y requieren resultado cancelled, no recuperación por timeout. Las
medidas de latencia son observaciones, no un umbral de tiempo real.

Se ejecuta en normal, ASan/UBSan y TSan; este último enlaza el QtCore 6.11.1
instrumentado de SRC84. El diagnóstico dyld confirma la biblioteca cargada.
Cuatro mutantes de integración omiten el aviso, lo retiran antes de la llamada,
omiten la ruta directa o eliminan la cancelación PINE; un quinto mutante del
núcleo borra todas las reservas al salir de un scope anidado. Deben fallar con
una aserción específica y dejar el grupo de procesos limpio.

La primera fixture exigía estado released para GS aunque la cancelación podía
ocurrir antes de solicitarlo. Se conservó el fallo y se separaron las dos
intercalaciones. Un primer mutante PINE no llegó al compilador por la precedencia
de includes locales; se conserva como control no efectivo y el final copia el
soporte en la carpeta del mutante para resolver el fragmento alterado.

Estos ensayos no acreditan callbacks arbitrarios sin locks, QWidget completo,
VM, captura global ni ejecución Nintendo. Ver [informe](../../../docs/execution/f02-07-external-waits.md).
