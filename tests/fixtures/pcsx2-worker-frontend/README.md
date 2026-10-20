# Frontend entre hilos

Fixture propia que compone la preparación de SRC83, sin su main, mediante un
fragmento propio privado. Añade cuatro cuerpos exactos de despacho CPU/UI del
proveedor y receptores QObject de prueba; 68 fragmentos PCSX2 en total.

El hilo principal ejecuta UI y QThread ejecuta CPU. VU y GS conservan sus bucles
exactos, WorkSema/Mach y efectos dobles descritos en SRC83. Hay tres escenarios:
GS→UI síncrono con UI disponible, operación UI→CPU encolada durante drenaje y
espera circular UI→CPU / GS→UI recuperada por plazo. Se verifica entrega única,
payload, afinidad, efecto anterior al retorno síncrono y retiro previo al productor.

Las pruebas positivas usan normal, ASan/UBSan y TSan con QtCore compilado también
con TSan, incluyendo Objective-C++ de Darwin. Se verifica la biblioteca cargada.
La ejecución inicial contra QtCore sin instrumentar produjo un aviso, que se
conserva. No se añaden supresiones ni barreras artificiales al despacho Qt.

Los negativos convierten un retorno bloqueante en asíncrono y duplican la entrega
CPU; ambos deben fallar en aserciones específicas y terminar bajo supervisión.
Estos receptores no son MainWindow/EmuThread completos ni renderizan ventanas.
