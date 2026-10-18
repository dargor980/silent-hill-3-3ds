# Fronteras de carga — LF01–LF08

Unidad LP-C de [LP01–LP10](load-provenance-v1.md). Esta iteración valida
capturas suministradas de una llamada y su retorno. La identidad del archivo,
el descriptor activo, la ruta de caché/disco y la adquisición real siguen
siendo condiciones adicionales para construir un evento `Read`.

## Requisitos EARS

- **LF01:** CUANDO examine una ruta candidata, el investigador DEBERÁ fijar
  ventanas ELF/estado por hash y separar referencias estáticas de ejecución.
  Un descriptor cerrado o residual SHALL NOT identificar el archivo activo.
- **LF02:** CUANDO valide una pausa multirrango, el adaptador DEBERÁ exigir
  entre uno y ocho rangos con etiquetas únicas, planes AC válidos, secuencias
  consecutivas y un único estado/hash, slot, proceso, sesión, entorno, PC y
  ciclo. DEBERÁ contrastar los tres paquetes de cada rango con ese estado.
- **LF03:** CUANDO normalice un rango, DEBERÁ comprobar AC/MP en todas sus
  páginas, respaldo esperado y anclas compartidas. Las entradas de una página
  virtual observada en varios rangos DEBERÁN coincidir. Código y destino
  DEBERÁN estar cubiertos expresamente; igualdad de bytes no prueba un alias.
- **LF04:** CUANDO valide una llamada, DEBERÁ exigir dos pausas con código y
  destino, identidad estable, slots diferentes, secuencia consecutiva y ciclo
  creciente dentro de 60 segundos EE. DEBERÁ mantener iguales los mapas de
  esos rangos entre las dos pausas, sin afirmar continuidad entre instantes.
- **LF05:** CUANDO acepte el sitio, DEBERÁ comprobar JAL directo, destino fijado,
  doce bytes de código iguales en ambas pausas (llamada, slot e instrucción
  de retorno, sin afirmar que esta última se ejecutó), PC de llamada/retorno, SP
  conservado y RA de retorno. El delay slot soportado será NOP o DADDU hacia
  GPR6 desde GPR0–30 y cero; DEBERÁ rechazar el resto, incluido GPR31.
- **LF06:** CUANDO concilie argumentos, DEBERÁ aplicar el delay slot soportado
  antes de contrastar destino GPR5 y tamaño GPR6; el retorno GPR2 DEBERÁ igualar
  exactamente el tamaño solicitado de 1–4.096 bytes. Lectura corta, error,
  tamaño excesivo y rango cambiado DEBERÁN rechazarse. GPR4 no constituye por
  sí solo identidad de archivo.
- **LF07:** CUANDO publique, DEBERÁ limitarse a hashes, tamaños y resultados.
  DEBERÁ declarar autenticación no provista, archivo/disco/carga pendientes,
  vínculos/capacidades vacíos y ausencia de eventos `Read` producidos. Un destino
  sin cambios podrá ser coherente, pero SHALL NOT probar una nueva lectura.
- **LF08:** CUANDO cierre la unidad, DEBERÁ usar fixtures propios para mapas de
  código/datos, cruces de página, alias, identidad, estado, instrucciones,
  delay slot, retorno corto y límites; ejecutar regresión y gate 80/80, y
  conservar dos análisis estáticos idénticos sin publicar originales.

## Diseño y tareas

`mapped_pause` valida los paquetes y el estado de varios rangos de una pausa;
devuelve datos privados tipados sin I/O ni control del emulador. `load_call`
consume esas pausas y comprueba una frontera ABI pequeña. Ninguno identifica
archivos ni introduce procedencia en `load_lineage`. Custodia, adquisición,
adaptación de descriptor/archivo y publicación conservan responsabilidades
separadas. No se aceptan flags suministrados como prueba de traducción.
El control de código cubre llamada/slot/retorno, no el cuerpo del destinatario;
su ejecución y semántica de lectura requieren evidencia adicional.

1. Fijar ruta y llamadas candidatas; registrar rutas de caché y truncamiento.
2. Implementar pausa multirrango y conciliador de llamada, con pruebas propias.
3. Vincular descriptor activo, apertura/posición y archivo a esas capturas;
   seleccionar rutas de caché/disco y cualquier transferencia adicional.
4. Incorporar adquisición multirrango con un estado común y guardia/custodia;
   ejecutar LP-D desde antes de la carga solo después de cerrar el plan.

Los pasos 1–2 constituyen una unidad comprobable de LP-C; no completan 3–4.

Estado SRC56: pasos 1–2 completados con 68 casos propios y dos análisis
estáticos idénticos. [Informe y siguiente tarea](../docs/execution/f02-07-load-frontier.md).
La adquisición multirrango deberá presupuestar también hasta 256 solicitudes
regionales por sesión; ocho rangos por pausa no autorizan exceder ese límite.
