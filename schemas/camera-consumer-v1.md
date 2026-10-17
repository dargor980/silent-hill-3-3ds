# Consumidor candidato ELF/MIPS v1

Instancia F02.07/camera-consumer-eu; RF02.02/.07/.08, RNF06.01/.04/.07,
RNF07.06-.09 y RNF11.05-.09. Este contrato produce indicios estáticos, no un
decoder SH3 ni una prueba de ejecución. No requiere exportar el ejecutable.

## Requisitos EARS

- **CE01:** WHEN inicia un sondeo THEN la herramienta SHALL fijar SHA-256 de
  perfil, ISO y sondeo de cámara, reconciliar imagen/perfil entre ellos y verificar
  BOOT2, tamaños y hashes completos de SYSTEM.CNF y su ejecutable antes de parsear.
  El conjunto de rutas SHALL coincidir con el perfil; otros miembros no se
  inspeccionan individualmente. No se modifica evidencia previa.
- **CE02:** WHEN interpreta el ejecutable THEN el parser SHALL aceptar únicamente
  ELF32 little endian ET_EXEC/MIPS versión 1, archivo de 52 bytes a 16 MiB,
  tabla de 1..128 program headers de 32 bytes, dentro del archivo. No interpretar
  secciones, símbolos, relocaciones, overlays ni ABI completo.
- **CE03:** WHEN registra PT_LOAD THEN SHALL comprobar rango de archivo, tamaño
  de memoria, overflow de 32 bits y alineación congruente; SHALL rechazar solapes
  de bytes de archivo y cualquier memoria ajena que intercepte bytes respaldados.
  Los solapes solo entre regiones sin bytes se registran sin resolver su carga.
  IF una dirección cae en BSS, un hueco o cruza segmentos THEN su traducción SHALL
  fallar; no fabricar bytes cero. La entrada SHALL tener cuatro bytes respaldados
  por un segmento ejecutable y estar alineada a cuatro.
- **CE04:** WHEN explora segmentos ejecutables THEN SHALL leer solo bytes
  respaldados en bloques <=4096, con solape de 20 bytes, presupuesto total de
  segmentos <=16 MiB y <=1024 coincidencias. SHALL evitar duplicados y patrones
  partidos entre segmentos. PF_X no demuestra que todos esos bytes sean código.
- **CE05:** WHEN seis palabras alineadas cumplen la secuencia de búsqueda propia
  THEN SHALL registrar exclusivamente posición, hash de ventana y destino de salto:
  avance del mismo registro por +128 mediante ADDIU/DADDIU, NOP, LW relativo +68,
  ANDI inmediato 1 sobre su resultado, BEQ resultado/zero hacia atrás y NOP en delay
  slot. Registros base/cargado/máscara SHALL no destruir el puntero ni usar zero
  como destino. Destino SHALL pertenecer al mismo segmento respaldado.
  Esta secuencia restringida puede omitir variantes válidas.
- **CE06:** WHEN hay coincidencia THEN SHALL conservar estado
  `syntactic_candidate`, vínculo a recurso `unproven`, capacidades vacías y F02.07
  pendiente. No inferir función, accesibilidad, puntero de entrada, campos 92/108,
  cola, unidades, salas ni comportamiento. Incluso datos propios con ese patrón
  pueden coincidir sin ser un consumidor de cámara.
- **CE07:** IF lectura/identidad/transporte/presupuesto falla THEN SHALL abortar
  íntegramente sin publicar resultado parcial; el adaptador SHALL comprobar
  estabilidad al cerrar antes de publicar JSON exclusivo. No sobrescribir salidas.
- **CE08:** WHEN verifica la herramienta THEN SHALL usar ELF e instrucciones
  sintéticas propias, cubrir límites, endianness, BSS, solapes, targets, registros,
  delay slots, fronteras de bloque y fallo tardío. Dos inspecciones reales SHALL
  compararse byte a byte; no guardar payload, desensamblado, cadenas o tablas del
  juego en código, fixtures, logs públicos ni CI.

## Diseño y tareas

1. `elf32.py`: modelo inmutable y parser sobre un puerto de lectura por rangos;
   traducción VA a offset, sin filesystem ni conocimiento de cámara.
2. `mips_camera.py`: reconocimiento puro del patrón propio y barrido acotado del
   mapa; salida de metadatos. No pretende implementar un desensamblador R5900.
3. `camera_consumer.py`: vinculación de identidad, composición con IsoImage y
   publicación existente. La CLI fija hashes; cada responsabilidad es sustituible.
4. Pruebas sintéticas, doble sondeo, quality/cobertura y reporte con límites.
5. Si falta vínculo al recurso, siguiente instancia: procedencia del puntero y
   referencias entrantes en los sitios candidatos, antes de versionar semántica.

Fuentes primarias consultadas: [ELF header](https://gabi.xinuos.com/elf/02-eheader.html),
[program loading](https://gabi.xinuos.com/elf/07-pheader.html) y codificación en
[MIPS/binutils](https://github.com/MIPS/binutils-gdb/blob/9decc44bc67d9fb4248c2afe4fde77174e8abf80/opcodes/mips-opc.c).
Código propio usando struct/stdlib, sin dependencia ni código externo incorporado.
