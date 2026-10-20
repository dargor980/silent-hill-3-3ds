# Admission profile v1 — AP01–AP08

Unidad AD-1 de LG-I2: diagnóstico previo de compatibilidad, sin permiso de captura.

## Requisitos EARS

- **AP01:** WHEN se inspecciona un perfil THEN el adaptador SHALL obtener los
  hechos del proveedor y SHALL NOT aceptar declaraciones del cliente como prueba.
- **AP02:** IF la llamada no pertenece al hilo CPU inicializado THEN SHALL
  rechazar el contexto sin leer configuración ni punteros CPU compartidos.
- **AP03:** WHEN hay ejecución CPU activa o una transición de implementaciones
  pendiente THEN SHALL declarar incompatible la frontera. Paused por sí solo
  SHALL NOT acreditar salida de CPU ni drenaje de trabajos.
- **AP04:** WHEN se evalúan CPU EE/IOP/VU THEN SHALL comprobar tanto la opción
  configurada como la implementación seleccionada; punteros nulos, recompiladores
  y replayer SHALL NOT satisfacer el perfil de intérpretes.
- **AP05:** IF caché EE, fastmem, MTVU, VIF dinámico o RAIntegration están activos
  THEN SHALL registrar todas las incompatibilidades observadas, sin ocultar otras.
- **AP06:** IF exclusión de PINE, RDebug, GS/VU u otros escritores no está
  demostrada THEN SHALL conservar el hecho como desconocido. Un indicador de
  parada o una cola aparentemente vacía SHALL NOT convertirse en exclusión.
- **AP07:** WHEN se evalúa un hecho ausente o con un valor no reconocido THEN
  SHALL tratarlo como desconocido. Todos los requisitos SHALL evaluarse; resultados
  anteriores SHALL NOT completar datos de la siguiente inspección.
- **AP08:** WHILE falte exclusión integral y unión con época/extremos THEN el
  diagnóstico SHALL NOT crear conexiones, armar guardias ni otorgar capacidades.
  Un resultado sin obstáculos en un fixture solo acredita el evaluador puro.

## Diseño y SOLID

`AdmissionProfile` es un vector fijo de hechos tipados, inicialmente desconocidos.
`assess_profile` produce máscaras separadas de incumplimientos y desconocidos;
no tiene referencias al emulador, locks, estado mutable ni efectos de captura.
El adaptador privado traduce estado/configuración/punteros a esos hechos.
La API es interna, sin comando PINE ni serializador público.

El adaptador solo lee campos no atómicos tras comprobar una marca local al hilo,
activada al terminar CPUThreadInitialize y retirada al entrar CPUThreadShutdown.
Un ámbito RAII alrededor de Execute conserva la marca de ejecución durante
cambios de CPU y ejecución anidada. Esta marca detecta reentrada, pero no excluye
otros hilos. Ninguna lectura intenta inferir finalización GS/VU o cierre PINE.

El perfil inicial es deliberadamente restrictivo: todos los intérpretes,
sin caché EE, fastmem, MTVU ni VIF dinámico. La fuente fijada tiene VIF dinámico
habilitado; este lote no cambia esa opción ni declara una VM admitida.
RDebug y otros escritores permanecen desconocidos aunque el inventario estático
no muestre su enlace. Su ausencia debe verificarse en la aplicación final.

## Tareas y aceptación

1. **AP-T1 / AP01,03–06:** fijar fuentes y matriz de condiciones, identificar
   transiciones de pausa/PINE y diseñar el siguiente protocolo de exclusión.
2. **AP-T2 / AP01–08:** implementar evaluador puro y sampler privado; conservar
   copias anteriores, efectos del proveedor y snapshots públicos históricos.
3. **AP-T3 / AP02–08:** probar hechos desconocidos/inválidos, combinaciones,
   contradicción config/puntero, transición, reentrada y otro hilo; distinguir
   funciones reales seleccionadas de dependencias simuladas.
4. **AP-T4 / AP07,08:** compilar ON/OFF, sanitizar harness, comprobar cobertura,
   regresión, custodia y dos auditorías iguales. Mantener AD-2–AD-4 pendientes.
