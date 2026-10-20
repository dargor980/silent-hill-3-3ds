# IT — Margen temporal del inventario

Historia: como investigador, necesito medir qué fases consumen el plazo del
diagnóstico, incluida su variación y el coste de observarlas, antes de optimizar.

## Requisitos EARS

- **IT01:** WHEN se mida una sesión THEN SHALL conservar el plazo global de
  cinco segundos, los plazos por respuesta, verificadores, doble comprobación,
  identidades y decisiones ordinarias. No SHALL omitir hashes ni reutilizar un
  resultado anterior como prueba de identidad actual.
- **IT02:** WHEN se mida una fase THEN SHALL usar reloj monotónico y asociar
  duración, número de llamadas y estado parcial a la consulta correspondiente.
  SHALL separar preparación, manifiestos, orígenes, digest final, entrega y cierre;
  no SHALL sumar tiempos inclusivos superpuestos como coste total.
- **IT03:** IF un intento falla o vence THEN SHALL conservarlo con sus fases
  alcanzadas, frames realmente aceptados, causa y limpieza. Una muestra parcial
  no SHALL contarse como inventario completo ni como coste de una sesión exitosa.
- **IT04:** WHEN se contraste instrumentación THEN SHALL reutilizar el candidato
  limpio fijado y comparar sonda gruesa/fina, con repeticiones y orden alternado.
  SHALL medir el coste básico del reloj/registro, declarar ruido y tamaño de
  muestra, y no inferir percentiles poblacionales o garantías de tiempo real.
- **IT05:** WHEN se atribuya coste o se proponga una optimización THEN SHALL
  mostrar evidencia por fase y distinguir medición de hipótesis. Cualquier cambio
  funcional SHALL tener diseño, regresiones y control limpio propios antes de
  adoptarse. Los gates y captura SHALL permanecer cerrados.

## Diseño

La sonda solo modifica copias privadas. Acumula contadores en almacenamiento
fijo por hilo DW, consulta (preparación y hasta tres muestras) y fase. Dos lecturas
del reloj delimitan cada intervalo; la impresión ocurre al cerrar Work, después
de la última muestra. La sonda fina añade lectura de archivos, SHA y estabilidad
de orígenes; la gruesa conserva únicamente fases amplias. No llama adicionalmente
a `DiagnosticBudget`, no cambia retornos ni introduce espera en CPU/DW.

Se registran por separado hitos IO de inicio/plazo global, binding, entregas y
limpieza. Se usan timestamps del mismo reloj monotónico y la metadata ordinaria
del consumidor. La calibración del registro corre antes del servicio: informa
coste local, sin descontarlo artificialmente de las mediciones ni garantizar un
límite superior. La comparación limpia permite observar perturbación total.

Matriz fijada antes de ejecutar: limpio/gruesa/fina, dos repeticiones por variante
y condición; orden limpio→gruesa→fina y fina→gruesa→limpio. Condiciones: sin carga
añadida y con un proceso propio de carga CPU, memoria acotada y tiempo supervisado.
Son doce sesiones; no se presume caché fría ni host inactivo. La carga añadida se
identifica y termina al cerrar cada sesión. Todos los resultados se conservan.

## Tareas y presupuesto IT-B

- [x] **IT-T1:** fijar base SRC127/SRC126, contrato, fases, matriz y controles.
- [x] **IT-T2:** sonda de memoria fija, inserciones verificables y parser estricto;
  probar fases, nesting, límites, metadatos inválidos y resultados incompletos.
- [x] **IT-T3 / RT-T3c.2:** compilar copia observada, ejecutar doce sesiones y
  auditar margen global/por consulta, coste de sonda y distribución por fase.
- [x] **IT-T4:** documentar causa medida, decisión sobre optimización, límites y
  siguientes tareas; conservar fallos y hashes sin habilitar captura.

Hasta dos bundles y fuentes/objetos/logs ≤512 MiB combinados; inicio ≥11 GiB,
suelo/preflight por comando ≥10 GiB. Build ≤600 s, comando ≤180 s, sesión ≤100 s,
matriz ≤900 s, muestras cada 0,5 s. Pruebas propias ≤256 MiB. Una carga CPU por
sesión cargada, búfer ≤8 MiB, termina con su proceso supervisor. No se compilan
dependencias; IB02 de build completo permanece en 20 GiB.
