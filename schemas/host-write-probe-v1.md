# Host write probe v1 — HW01–HW08

Lote LG-I1 de productores host. Su finalidad es impedir que una modificación
directa quede oculta a la guardia de continuidad durante la investigación.
No habilita armado ni acredita cobertura exhaustiva del emulador.

## Requisitos EARS

- **HW01:** WHEN el inventario encuentra un escritor host THEN SHALL registrar
  función, destino, longitud, condición, contexto de ejecución y delegación;
  SHALL distinguir fuente activa, opcional, no compilada y operación de ciclo de vida.
- **HW02:** WHEN los hooks de arranque sustituyen separadores o copian nombres y
  argumentos THEN SHALL avisar del destino host resuelto y longitud antes de cada
  efecto; las copias de cadenas SHALL incluir el terminador. SHALL conservar
  límites, retornos, registros y escrituras posteriores aunque la guardia falle.
- **HW03:** WHEN la llamada HLE Deci2 limpia su palabra de estado THEN SHALL
  notificar esos cuatro bytes antes de asignar. IF la rama no escribe THEN SHALL
  NOT emitir un aviso de memoria por esa operación.
- **HW04:** WHERE se habilita RAIntegration, WHEN su callback escribe un byte
  dentro del rango permitido THEN SHALL notificar el destino antes del efecto;
  IF rechaza el rango THEN SHALL conservar el rechazo sin inventar una escritura.
- **HW05:** WHEN la descarga de una entrada válida de la tabla auxiliar de TLB
  remapea memoria y modifica la tabla THEN SHALL invalidar conservadoramente
  antes del primer remapeo. IF no encuentra una entrada válida coincidente THEN
  SHALL conservar el comportamiento sin aviso nuevo.
- **HW06:** WHEN un escritor delega a una hoja VTLB ya instrumentada THEN SHALL
  evitar un aviso duplicado; SHALL conservar rechazo previo, escritura parcial y
  semántica idempotente. Un valor igual solo cuenta como escritura si existe efecto.
- **HW07:** WHEN se valida el lote THEN SHALL ejecutar cuerpos exactos privados
  con datos propios, comparar efectos ON/OFF y ejecutar sanitizadores; SHALL
  distinguir dobles, compilación real, ramas opcionales y prueba de VM.
- **HW08:** WHILE no estén demostrados serialización de efectos, época, cierre
  de escritores y cobertura completa THEN SHALL mantener vacíos los modos admitidos
  y SHALL NOT promover un sello del núcleo a continuidad real.

## Diseño y SOLID

La guardia decide invalidez; `PhysicalWrites` traduce direcciones; los productores
solo avisan antes del efecto. Se reutilizan ambos componentes y la conexión RAII,
sin dependencias de PCSX2 en el núcleo portable. Cada destino directo se resuelve
una sola vez. La instrumentación desaparece con el flag OFF.

Depurador, PINE y parches conservan sus hojas VTLB: no se instrumentan dos veces.
El callback RAIntegration se ensaya separado de la aplicación Windows; compilar
Achievements en macOS no verifica esa rama condicional. La descarga de la tabla
auxiliar usa `lost` porque el remapeo exige el protocolo de época futuro.

Reset, restauración, remapeos generales, cambios de modo y cierre pertenecen a
LG-I2. RDebug no incluido en el build fijado y otras configuraciones permanecen
fuera de admisión. PINE escribe desde su hilo servidor; el mutex del puente solo
serializa avisos, no los efectos ni el acceso concurrente a la guardia. El lote
no convierte esa ruta en segura para armar una captura.

## Tareas y aceptación

1. **HW-T1 / HW01,06,08:** fijar inventario y hashes; identificar hojas cubiertas,
   escritores directos, configuración de compilación e interferencias de ciclo de vida.
2. **HW-T2 / HW02–06:** crear copia privada nueva y parche reversible; observar
   seis efectos de arranque, Deci2, callback opcional y descarga auxiliar TLB.
   Mantener anteriores fuentes y no modificar configuración ni bundle instalado.
3. **HW-T3 / HW02–07:** probar cuerpos reales con fixtures propios: separadores,
   terminador, límite de argumentos, ramas sin efecto, memoria ajena, escritura
   igual/restaurada, alias, cruce de página y fallo después de un efecto parcial.
   Registrar el orden anterior al efecto y efectos equivalentes ON/OFF/sanitizadores.
4. **HW-T4 / HW07,08:** compilar unidades ON/OFF, comprobar símbolos y custodia
   mediante dos auditorías iguales; ejecutar gates host/Python. Documentar por
   separado ramas opcionales sin build de plataforma, protocolo IPC no ensayado,
   cobertura completa pendiente y siguientes tareas de ciclo de vida.
