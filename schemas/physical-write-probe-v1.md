# Physical write probe v1 — PW01–PW07

Primera integración de LG-I1: observar las escrituras de VTLB sobre su destino
host efectivo. No completa el inventario de escritores ni habilita continuidad
real. JIT, DMA, caché, ciclo de vida, extremos y transporte siguen pendientes.

## Requisitos EARS

- **PW01:** WHEN llega una escritura mapeada THEN el puente SHALL resolver su
  intervalo contra el bloque host de RAM EE sin desreferenciarlo; SHALL rechazar
  anclas inválidas, tamaño cero, overflow y cruces parciales del bloque.
- **PW02:** WHEN el intervalo está completamente dentro de RAM EE THEN el puente
  SHALL suministrar su offset físico y tamaño a LG antes de la escritura; WHEN
  es completamente ajeno THEN SHALL ignorarlo sin consumir un número de evento.
- **PW03:** WHEN llega una escritura por caché o handler no cubierto THEN el
  puente SHALL invalidar el intervalo como pérdida de cobertura antes del efecto,
  sin impedir ni modificar el comportamiento original del emulador.
- **PW04:** WHEN se instala una conexión de prueba THEN el registro SHALL aceptar
  como máximo una, serializar sus callbacks y esperar su terminación al desconectar;
  SHALL impedir copia/movimiento y no reemplazar una conexión activa.
- **PW05:** WHILE no hay conexión THEN los hooks SHALL ser inertes. WHEN se
  compila sin la opción del observador THEN el proveedor SHALL conservar sus
  funciones originales sin referencias a los hooks nuevos.
- **PW06:** WHEN se instrumenta VTLB THEN SHALL cubrir escritura escalar, 128 bits,
  `ramWrite` y cada fragmento de `memSafeWriteBytes`; SHALL conservar el orden,
  los valores y los retornos originales, incluidos errores después de una copia parcial.
- **PW07:** WHEN se publica evidencia THEN SHALL distinguir pruebas propias,
  ejecución de funciones extraídas del proveedor fijado, compilación de unidades
  reales y ejecución del emulador completo; SHALL mantener JR cerrado hasta
  acreditar todas las rutas habilitadas y el ciclo de vida.

## Diseño y límites

`PhysicalWrites` traduce destinos host ya resueltos a offsets físicos y compone
`LifetimeGuard`. No recibe direcciones virtuales ni lee RAM; dos aliases que
resuelven al mismo puntero producen el mismo offset. La secuencia se deriva del
último evento aceptado. Esto ordena callbacks recibidos, no detecta callbacks
omitidos por una ruta sin instrumentar. La sesión/época procede del plan LG;
el ciclo lo suministra el punto de escritura del proveedor.

`WriteBinding` conecta una instancia mediante RAII. Un mutex protege el registro,
los callbacks y la desconexión; el guardia y el puente deben vivir más que la
conexión. El emulador continúa su escritura incluso si la observación falla.
Este mutex no abarca el efecto de memoria posterior: no demuestra serialización
global de escritores ni sustituye LG-I2. El acceso directo al guardia durante una
conexión exige la misma coordinación externa que LG.

La integración no expone comando PINE de armado ni se instala automáticamente en
una VM. Los fixtures conectan explícitamente el puente; no hay modo de captura
real autorizado por este contrato. La admisión de modos y el armado se habilitarán
solo después de completar la matriz de cobertura, época host y extremos.

## Tareas

1. **PW-T1 / PW01–05:** implementar traducción de intervalos y conexión RAII;
   probar bordes, aliases, escritura igual, cobertura desconocida y concurrencia.
2. **PW-T2 / PW06:** crear copia privada nueva del proveedor instrumentado,
   preservar fuente anterior y añadir hooks previos a las cuatro rutas VTLB.
3. **PW-T3 / PW05–07:** compilar unidades reales ON/OFF y ejecutar las funciones
   originales instrumentadas en un harness privado con RAM propia y dobles
   explícitos de mapa/caché/handler. Verificar notificación previa, orden y efectos.
4. **PW-T4 / PW07:** ejecutar host Debug/Release/sanitizadores, cobertura y
   regresión; publicar hashes, matriz de rutas restantes y siguiente tarea.
