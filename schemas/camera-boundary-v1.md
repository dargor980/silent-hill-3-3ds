# Fronteras de llamadas MIPS v1

F02.07/camera-caller-boundary-eu; extiende la investigación CP01-CP08 sin modificarla.
No es un emulador ni un contrato del formato de cámara.

## Requisitos EARS

- **CB01:** WHEN inicia THEN SHALL fijar ISO, perfil, sondeo, consumidor y ambas
  copias del informe de punteros por SHA-256; SHALL exigir igualdad entre las copias
  y regenerar la cadena desde la ISO antes de usar posiciones privadas.
- **CB02:** WHEN selecciona fronteras THEN SHALL deduplicar referencias externas y
  llamadas por sitio/PC/registro, conservar los estados aritméticos previos y limitar
  a 16 fronteras. SHALL validar mapeo ejecutable respaldado; PF_X no prueba código.
- **CB03:** WHEN estudia una llamada directa THEN SHALL distinguir procedencia antes
  de llamar, después del delay slot antes de entrar, y continuación hipotética tras
  retorno. SHALL aplicar enlace y slot en ese orden; un slot de control SHALL quedar
  desconocido. SHALL conservar referencias externas a la ventana del llamador.
- **CB04:** WHEN resume el destino THEN SHALL explorar ambas salidas de ramas,
  aplicar slots normales/likely correctamente y reconocer retorno solo por JR GPR31
  con procedencia de retorno conservada antes del slot. SHALL limitar a 4096 bytes,
  1024 estados y profundidad 256; no inferir final de función por proximidad.
- **CB05:** IF encuentra operación desconocida, llamada anidada, indirecto distinto
  del retorno, salida de ventana, ciclo/convergencia repetida o límite THEN SHALL
  conservar frontera explícita y no declarar preservación global. No asumir ABI.
- **CB06:** WHEN determina preservación THEN SHALL referirse solo a identidad de los
  32 bits bajos del GPR en el modelo estático. Copias soportadas propagan identidad;
  cargas, ajustes y otras escrituras la vuelven desconocida. Guardar/restaurar desde
  memoria SHALL permanecer desconocido: sin prueba de alias/contenido, no recuperar
  identidad. SHALL declarar preservado solo con retornos y todas las rutas cerradas
  y preservadas. Esto no acredita ejecución, ausencia de excepciones ni memoria.
- **CB07:** WHEN una procedencia termina en carga THEN SHALL separar la dirección de
  la instrucción, registro base y contenido dinámico; no inventar valor o recurso.
  SHALL emitir un plan privado de observación con puntos, registros, rangos de código
  y hashes esperados, sin afirmar haber capturado datos. Sin identidad de recurso,
  colas/92/108, capacidades y F02.07/Q05/G02 SHALL permanecer pendientes.
- **CB08:** WHEN publica THEN SHALL emitir solo metadatos privados tras cierre estable,
  exclusivamente y sin originales. IF falla identidad/I/O/presupuesto estructural
  THEN SHALL abortar sin publicar. SHALL verificar fixtures propios de slots, retornos,
  guardado/restauración, salidas divergentes, llamadas/recursión, límites y mapeo;
  equivalencia memoria/ISO, repetición, calidad y cobertura en el pipeline existente.

## Diseño y tareas

1. Contrato: estos requisitos preceden al código. Reutilizar fuentes MIPS fijadas,
   sin nuevas bibliotecas ni cambio en inspectores históricos.
2. `callee_flow`: análisis puro de identidad GPR y control, con retornos/fronteras
   explícitos. Profundidad interprocedural uno: no entrar en llamadas anidadas.
3. `call_boundary`: selección, lectura acotada por puerto, referencias del llamador,
   tres consultas de estado y plan de captura. Ventana del llamador: hasta 512 bytes
   anteriores y 12 desde la llamada; cada lectura <=4096 bytes. Referencias heredan
   límites CP02/CP03; trazas del llamador heredan CP06.
4. `camera_boundary`: reconciliar informes e identidad, componer ISO y publicación.
5. Fixtures/regresiones → dos sondeos reales → evidencia, custodia y siguiente tarea.

La ventana del destino es un presupuesto de exploración, no un tamaño de función.
Los resúmenes no eliminan automáticamente barreras del informe histórico ni prueban
un consumidor. Un retorno con identidad desconocida no significa valor diferente.
