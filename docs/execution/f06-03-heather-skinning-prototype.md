# F06.03 / HS-T3 — prototipo híbrido y ensayo host

**HS-T3 completada en host.** Se implementó HSN v1 con selección explícita
`SkinningMode::cpu/hybrid`, preparación atómica y fallback completo a CPU
ante fallo de carga. Sigue **HS-T4**, integración de la selección en la
aplicación ARM, verificación del ABI y paquete comparativo. La consola
conserva `0188790baedd`; no se generó un nuevo paquete ni se escribió a SD.
HM-T5 adicional y pared 60 siguen aplazadas.

## Implementación

`skinning_plan` valida primero el recurso SRI, cuenta las capacidades y
solo después llena buffers distintos del modelo. Conserva materiales y
triángulos, paletas ordenadas de hasta 30 identidades y remapeo por primera
aparición dentro del lote. Helpers mantienen el desplazamiento fijo 73.
El vértice de 64 bytes tiene aserciones de tamaño, alineación y offsets.
La preparación de filas conserva el orden numérico y desactiva contracción
FMA; los uniformes se escriben mediante `FVec4_New`, respetando W/Z/Y/X.
El shader de producción coincide con la sonda congelada; su gate rechaza
cualquier SHBIN cuyo tamaño o hash difiera del contrato.

El adaptador prepara VBO e índices directamente en memoria lineal durante
la carga. Publica el candidato completo o conserva CPU; comprueba las
ubicaciones 0/90 antes de acceder a uniformes. La validación CPU de todos
los vértices, incluida la geometría opaca, **se conserva**, junto con la
expansión completa de referencia. Esta versión no acredita eliminar ese
coste. Toda la instantánea de filas se prepara antes de `FrameBegin`.

El recorrido emite habitación, opacos de Heather y transparencias globales
CPU. Después de los opacos restaura programa, atributos y cámara CPU; cada
rango vuelve a seleccionar buffer, textura y estados. Esto evita que la
paleta c0..c89 altere la cámara c0..c3 del cabello/vidrio. La copia dinámica
espera propiedad y la destrucción sincroniza el target antes de liberar.
Los errores de cuadro mantienen la recuperación mediante L del bucle HM/HG.

## Equivalencia y fallos

- Los **54 vectores HSN** coinciden exactamente en bytes de vértices y
  uniformes. Evaluar el SHBIN binary32 con esos datos da un máximo de
  `6.867048796266317e-8` unidades frente al oráculo racional; W es exacta.
- Pasan las seis particiones congeladas, 64 planes aleatorios reproducibles
  y un caso de 8192 vértices fuente/18000 índices. Se comparan todos los
  índices, remapeos, materiales y bytes, además de rechazos y atomicidad.
- A/B se reautentican contra los manifiestos y hashes de HG/HS, con
  comprobación final de identidad de archivos y padres. Ambas producen
  **15 lotes, 6558 vértices, 15846 índices y 200 matrices sumadas por lote**.
  El cotejo nativo incluye todos los bytes del plan privado, sin publicar
  los recursos originales.
- Para 128 poses del recorrido privado por copia, el doble SDK evalúa los
  vértices indexados con los uniformes realmente enviados y los contrasta
  con el buffer CPU expandido. Máximo XYZ: `3.57627869e-7`; W exacta.
  Habitación y transparencias conservan bytes y orden exactamente.
- Se inyectan **seis fallos de asignación y 14 fallos SDK** de preparación,
  además de presupuesto insuficiente/modelo inválido, matrices inválidas,
  GPU ocupada, fallo de flush y de target. Se verifican fallback, cuadros
  sin publicación parcial, recuperación y liberación completa.
- El ensayo de recursos recorre **512 actualizaciones por variante y copia**
  con cinco acciones, pausa, paso único, reinicio y suspensión/restauración,
  prohibiendo asignaciones y liberaciones durante las actualizaciones.
  Las regresiones HM/HG conservan HOME/tapa y el manejo de R.

Estos resultados son C++ host y doble SDK. No emulan PICA24 ni comprueban
el resultado visual de la GPU. Proyección física de 0,25 píxel, fronteras
de clipping y visibilidad GPU deben comprobarse en HS-T4/T5; los cuatro
vectores de proyección HSN conservan sus umbrales y el rechazo no proyectable.

## Memoria y pila

| Medida privada host | CPU | Híbrida |
| --- | ---: | ---: |
| Presupuesto conservador, incluida reserva SDK | 51824452 B | 52313268 B |
| Residente observado C++ + doble SDK | 32183601 B | 32655561 B |
| Pico coexistente observado | 34252665 B | 34252665 B |
| Asignaciones durante 512 actualizaciones | 0 | 0 |

La candidata añade **488816 B** al presupuesto y queda en **49,89 MiB**,
bajo el umbral de 51,2 MiB (80 % de 64 MiB). VBO/IBO activos: 451404 B.
La reserva incluye plan, dos instantáneas de filas y workspace temporal;
se libera el staging de texturas antes de preparar el candidato. Por eso
el pico observado sigue siendo el de carga de texturas. No es RSS ni una
medición de memoria física 3DS; el ABI ARM se revalidará en HS-T4.

El inventario de pila abarca 26 unidades de producción, suma conservadora
de marcos, recursión acotada de ordenación y reserva externa de 8192 B:
**32704 B Clang y 29360 B GCC**, ambos bajo 32768 B. GCC también verifica
el grafo directo. La primera versión excedía el límite Clang (33152 B);
se movió el workspace de partición fuera de la pila sin aumentar el límite.
No se midió watermark físico ni se verificaron internamente las bibliotecas SDK.

## Intervalos y ensayo temporal

`WorkTrace` identifica cada llamada aceptada al bucle y entrega una muestra
sin asignaciones, incluso si queda pausada/suspendida o falla el render.
Los intervalos consecutivos comparten frontera y no se solapan. Se separan:
movimiento/contactos; selección/animación/pose; validación; paleta;
deformación CPU; ordenación/expansión; filas de habitación; espera de
propiedad; copia/flush; envío. Reintentos o varios pasos fijos acumulan sus
intervalos y conteos en la misma muestra. El total de la llamada y su
cadencia quedan aparte; la diferencia incluye trabajo no instrumentado.

El reloj determinista comprueba IDs sin huecos, conteos y duraciones. El
ensayo host privado alterna tres ventanas por variante: 32 cuadros de
calentamiento y 256 muestras cada una, **1536 muestras medidas, cero
cuadros fallidos**. Guarda mediana/p95/máximo por fase, total y cadencia.
Carga de archivos y preparación de recursos tienen campos separados;
audio no se ejecuta. GPU, vblank y cadencia física no se miden.

Los tiempos del envío incluyen las verificaciones del doble SDK, incluida
la evaluación de vértices; **no son una comparación de velocidad CPU/GPU**.
No se suma ningún tiempo GPU previo al CPU ni se declara una mejora.

## Validación reproducible

Apple Clang 21: 385 pruebas CTest completas y repetición de las afectadas
por los ajustes finales. ASan/UBSan: 32 regresiones y repeticiones finales
de integración/límites. GCC 12.2: 32 regresiones con cobertura y cinco
pruebas Release de contrato/integración/pila. Python: 374 pruebas HS/HG.
Se fijó también `-ffp-contract=off` en la referencia de equivalencia de rig
y `noexcept` en un callback de prueba para compatibilidad con glibc.

| Archivo | Líneas | Ramas |
| --- | ---: | ---: |
| skinning_plan.cpp | 100 % | 99,1 % |
| skinning_gpu.cpp | 98,8 % | 93,4 % |
| work_trace.hpp | 100 % | 100 % |
| room_renderer.cpp | 99,0 % | 95,7 % |
| room_scene.cpp | 99,5 % | 95,8 % |
| inspection_actor.cpp | 100 % | 100 % |
| room_loop.cpp | 100 % | 93,1 % |

El gate del shader tiene cobertura Python 100 %/100 %. CI incorpora los
gates individuales nuevos; no usa recursos privados. Ruff, formato C++,
contratos de repositorio y whitespace se verifican al cerrar esta instancia.

```sh
rtk proxy cmake -S . -B build/hs-host -DCMAKE_BUILD_TYPE=Release -DSH3_STACK_AUDIT=ON
rtk proxy cmake --build build/hs-host -j2
rtk proxy ctest --test-dir build/hs-host --output-on-failure
rtk proxy python3 tests/skinning_stack.py build/hs-host
```

Evidencia local: `build/heather-skinning-prototype/`,
`reports/local/heather-skinning-private-prototype-v1.json` y
`reports/local/heather-skinning-prototype-v1.json`, con fuentes, ejecutables,
fixtures, pruebas, cobertura, pila y ensayo temporal identificados por hash.
Se preservan los fixtures HSN/HG y el build HG entregado. HS-T4 debe preparar
una selección utilizable en consola y su paquete; HS-T5 decidirá sobre
rendimiento y límites con ejecución GPU real.
