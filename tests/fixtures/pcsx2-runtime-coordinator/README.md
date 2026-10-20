# Fixture propia RC

El harness incluye cuerpos exactos de VMManager, la rama Qt de despacho y los
controles propios VU/GS desde una copia privada. Los 15 prefijos de entrada VM y
los dos prefijos PINE se identifican como prefijos; no representan el resto de
sus operaciones. La compilación separada de unidades completas verifica sus APIs.

CPU, PINE, VM, configuración, colas vacías, efectos y Qt son dependencias locales
controladas. WorkerControl/RetainedDrain, hilos VU/GS y DW se ejecutan realmente;
no se ejecuta el emulador, renderer, BIOS ni juego. OFF contrasta los efectos
locales de esos prefijos con los hooks eliminados. La prueba Qt ejecuta la rama
real con event loop doble; el funcionamiento de Qt/VM enlazados queda para RB-T3.
