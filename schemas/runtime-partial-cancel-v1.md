# PC — Cancelación durante entrega parcial

Historia: como investigador, necesito que salir desde UI interrumpa también una
entrega en curso, sin aceptar respuestas truncadas ni destruir recursos activos.

## Requisitos EARS

- **PC01:** WHEN la señal de cancelación llegue durante entrega THEN SHALL
  observarse antes y después de cada llamada acotada al transporte; SHALL evitar
  iniciar la siguiente escritura al observarla. Los bytes ya enviados no se
  pueden retirar. No SHALL convertir un envío parcial en respuesta completa.
- **PC02:** WHEN se observe cancelación THEN SHALL conservar la primera causa
  terminal, revocar la sesión, retirar CPU y unir DW antes de destruir recursos
  IO; SHALL mantener UI viva hasta unir IO antes de detener CPU.
- **PC03:** IF el consumidor recibe un prefijo y EOF THEN SHALL rechazarlo con
  el validador ordinario, sin publicar diagnóstico ni habilitar captura.
- **PC04:** WHEN se pruebe una entrega parcial THEN SHALL acreditar bytes
  efectivamente enviados/recibidos, señal UI y orden de retirada. SHALL separar
  fragmentación/contrapresión inyectada de fragmentación espontánea del sistema.
  No SHALL ampliar plazos de producción ni sustituir coordinación por una espera
  arbitraria. Los resultados fallidos SHALL conservarse.
- **PC05:** WHEN no se solicite cancelación THEN SHALL conservar la API existente
  y sus plazos, validación de identidad, formato y tres respuestas ordinarias.

## Diseño y decisiones

La entrega síncrona puede consumir varios turnos de transporte de hasta 20 ms
antes de devolver el control al servicio. El servicio consulta su señal atómica
entre pasos; esa consulta no basta dentro de entrega. Se añade una sobrecarga
que recibe una referencia const a la señal, tanto en sesión como en entrega.
Las firmas previas siguen disponibles y usan la misma implementación sin señal
externa. No se modifica el layout de clases, ownership ni el protocolo.

La UI solo escribe la señal existente. IO la consulta y cancela el trabajador;
la sesión propaga la causa a handoff. Transporte, política de cancelación y
retirada conservan responsabilidades separadas. La observación es cooperativa:
una petición concurrente puede coincidir con la escritura ya iniciada, nunca
se promete retirar bytes que ya salieron ni evitar toda carrera con el último.

La sonda privada limita la primera escritura real a 1 o 293 de los 294 bytes.
Tras enviar ese prefijo, simula contrapresión devolviendo progreso cero en
turnos no mayores al presupuesto recibido. Un timer Qt activa ventana/Salir al
observar el prefijo y un archivo del consumidor que acredita su recepción.
No se espera indefinidamente, no se reinicia ningún reloj y la sonda no cancela
por sí misma. Este fallo se inyecta porque una respuesta tan pequeña normalmente
cabe completa en el socket; no demuestra contrapresión natural del sistema.

El consumidor conserva sesión/canal de SRC122. Un envoltorio de socket registra
lo devuelto por recv y crea el indicador después del prefijo, sin alterar bytes,
timeout, peer, EOF o reglas de aceptación. Se ejecutan dos perfiles por ruta y
prefijo, dos casos del candidato anterior y un control final sin sonda.

## Presupuesto PC-B y tareas

Hasta tres bundles incrementales y sus fuentes/objetos/logs, ≤512 MiB combinados.
Inicio de la secuencia ≥11 GiB; todos los comandos mantienen suelo y preflight
≥10 GiB. La reserva inicial cubre el máximo de 512 MiB más margen; no se requiere
recuperarla entre comandos de la misma secuencia acotada. Cada comando de build
≤180 s, secuencia de build ≤600 s, sesión ≤100 s, supervisión cada 0,5 s.
Regresiones nativas: cada etapa ≤512 MiB, inicio/suelo ≥10 GiB, comandos ≤180 s.
No se reconstruyen dependencias. IB02 de build completo sigue en 20 GiB.

- [x] **PC-T1:** fijar fuentes previas, reproducir con prefijo real y UI en
  candidato anterior; guardar causa y bytes. PC01–PC04.
- [x] **PC-T2:** implementar señal cooperativa dentro de sesión/entrega;
  regresiones para señal previa, lectura, cero progreso, prefijo y último byte,
  primera causa y ruta sin señal; CTest, sanitizadores y TSan. PC01–PC02, PC05.
- [x] **PC-T3 / RT-T3c.1b.partial-delivery:** ocho perfiles de VM real con
  contrapresión inyectada, cierre comprobado y respuesta rechazada; verificar
  retiro CPU, unión DW/IO y parada CPU; control ordinario sin sonda. PC01–PC05.
- [x] **PC-T4:** publicar evidencia, hashes, fallos y límites. Mantener separados
  Apagar VM, callbacks tardíos, margen temporal y gates de captura. PC04–PC05.

Resultado: [SRC125](../docs/execution/f02-07-partial-cancel.md). Ocho perfiles
corregidos rechazan el prefijo; el control sin sonda conserva tres respuestas.
