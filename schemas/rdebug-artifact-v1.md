# Ausencia de RDebug en un artefacto fijado — RD01–RD08

- **RD01:** WHEN se evalúa RDebug THEN SHALL identificar fuente, configuración,
  instrucciones de compilación/enlace y hash del ejecutable final. La ausencia
  de una referencia en una búsqueda textual SHALL NOT bastar por sí sola.
- **RD02:** WHEN la lista CMake declara fuentes RDebug THEN SHALL distinguir
  declaración de inclusión efectiva en targets. SHALL contrastar objetos,
  archivos de respuesta y archivos estáticos usados por el enlace.
- **RD03:** WHEN se examinan símbolos THEN SHALL conservar salida/hash y código
  de retorno de la herramienta, comprobar controles positivos y distinguir
  ausencia observada de símbolos eliminados/no inspeccionables.
- **RD04:** IF se detecta una unidad u objeto RDebug, falta un insumo esperado o
  falla una herramienta THEN SHALL rechazar la conclusión de ausencia.
- **RD05:** WHEN se verifica un candidato THEN SHALL comprobar también sus
  dependencias Mach-O empaquetadas y mantener los resultados ligados a sus hashes.
  SHALL NOT extrapolar a otro build, plataforma, plugin o instalación.
- **RD06:** WHEN se prueban controles negativos THEN SHALL detectar una entrada
  RDebug inyectada y un resultado incompleto, sin ejecutar servidor remoto ni VM.
- **RD07:** WHEN la auditoría concluye ausencia en el artefacto THEN SHALL emitir
  evidencia diagnóstica. SHALL NOT conceder capacidades, cambiar rdebug_excluded
  en producción ni sustituir la identidad del proceso que eventualmente capture.
- **RD08:** WHILE otros escritores, perfil, frontend o VM estén pendientes THEN
  SHALL conservar la admisión vacía y el transporte de armado cerrado.

## Diseño y tareas

La auditoría parte del candidato privado enlazado en IW-PINE-JOINT3. Inspecciona
la fuente RDebug, las entradas de compilación y los objetos del target/enlace,
y cruza ese inventario con símbolos del núcleo, ejecutable y dependencias.
Los símbolos DECI2 de servicios invitados no se confunden automáticamente con
el servidor RDebug: se fija una lista de símbolos específicos desde su fuente.

- **RD-T1:** fijar archivos de origen y listas CMake; resolver la pertenencia
  efectiva al target y comprobar los objetos generados.
- **RD-T2:** inspeccionar binario/archivos estáticos/dependencias, comprobar
  controles positivos y registrar resultados completos de las herramientas.
- **RD-T3:** probar entradas adversarias/faltantes, custodiar evidencia y dejar
  explícita la vinculación por hash aún pendiente en el proceso real.
