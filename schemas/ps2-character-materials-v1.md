# Texturas y vínculos del MDL — contrato candidato v1

F03.02, después de CM-T5e.1 funcional. Modelo `0x0209`, ordinal 142 de
XBG0.MFA, MDL SHA-256 `120cab2955727a3a86e916c345144183bec31570f2a5a92c430878e692014672`.
Historia: recuperar las imágenes que corresponden a la malla animada para
investigar su material original antes de incorporarlo al visor.

## Requisitos EARS

- **CT01** WHEN se adquiere el recurso, el coordinador SHALL verificar ISO,
  contenedor, selección y MDL por sus identidades existentes. SHALL producir
  dos salidas privadas independientes y conservar su comparación por hash.
- **CT02** WHEN se interpreta el sector de imágenes, el decoder SHALL comprobar
  recuentos cruzados, rangos, alineación, ausencia de solapamientos con malla,
  tablas y esqueleto, tamaño exacto, variante de transferencia y presupuesto
  de salida antes de decodificar píxeles. IF la tabla de imágenes no es la
  identidad del perfil observado SHALL rechazarla como variante pendiente.
- **CT03** WHEN se decodifica una imagen PSMT8 de este perfil, SHALL conservar
  índices y cuatro paletas RGBA, sin invertir filas ni modificar alfa original.
  Solo la vista PNG SHALL convertir alfa mediante `min(255, 2*a)` y declarar
  esa pérdida. SHALL rechazar PSMT4, transferencias o CLUT fuera del perfil.
- **CT04** WHEN se vincula una submalla, SHALL resolver descriptor → imagen y
  paleta dentro de sus límites y conservar partición opaca/blend, palabras
  originales y UV. No SHALL inferir mezcla, filtrado, iluminación o selección
  en ejecución a partir de esos campos ni de la apariencia de un PNG.
  IF el selector de paleta del descriptor no es cero SHALL rechazar esa
  variante: las cuatro unidades CLUT almacenadas no prueban su mapeo a CBP.
- **CT05** WHEN se publica el resultado, SHALL distinguir estructura, oráculo
  de píxeles, captura GS, integración y prueba física. SHALL dejar material GS
  y visor texturado pendientes hasta sus comprobaciones correspondientes.
- **CT06** WHEN se contrasta una captura GS, el auditor SHALL verificar sus
  identidades y correlacionar los comandos de cada submalla mediante STQ de
  la pose capturada, conservando orden, contexto y estados efectivos. IF un
  comando no tiene coincidencia única SHALL fallar sin atribuirle material.
- **CT07** WHEN se reproduce el dump en PCSX2, SHALL usar un perfil y salidas
  privados independientes y contrastar las tres texturas RGBA consumidas,
  vértices y estados con el dump. SHALL conservar alfa sin usarlo como prueba
  de mezcla; PRIM/TEST determinan si mezcla y descarte están habilitados.
- **CT08** WHEN se valida la semántica de color, SHALL comparar píxeles
  interiores con muestreo, modulación y niebla explícitos, declarar tolerancias
  antes del contraste e incluir controles negativos. SHALL separar esta
  evidencia de la iluminación dinámica, bordes y prueba física del visor.

## Diseño

Decoder puro `ps2_character_materials` compone los lectores MDL, sector de
textura e índices existentes; no modifica la malla ni accede a archivos.
Coordinador `decode_character_materials` usa `PairReader`, genera metadata y
previews y delega la escritura al writer privado exclusivo. Tests sintéticos
independientes del juego forman parte de la CI host existente.

Perfil: MDL v3 sin morph; hasta 16 imágenes y 256 descriptores. Sector final
con cabecera de 32 bytes. Tabla de imágenes consecutiva `0..n−1`; el significado
de otras variantes no se inventa. PSMCT32 → PSMT8, desplazamiento 1, cuatro
CLUT y dimensiones admitidas por el decoder existente. Presupuesto agregado
de hasta 1.048.576 píxeles de imágenes y otros tantos de texturas referenciadas.
Los originales y derivados permanecen fuera del repositorio.

Se exportan índices y las cuatro paletas de cada imagen, RGBA original/PNG
de cada descriptor y `materials.json` con enlaces y cabeceras conservadas.
El oráculo independiente debe contrastar el direccionamiento de índices con
tablas GS y la recuperación de paleta; invertir dirección de paleta o alterar
un píxel debe fallar. No se ejecuta código externo descargado.

Referencia de estructura, no autoridad de estado en ejecución:
[lector MDL de Murugo, revisión fijada](https://github.com/Murugo/Misc-Game-Research/blob/c088e878544f25d45ea7cf4215613fb5f9638dd4/PS2/Silent%20Hill%202%2B3/Blender/addons/io_sh2_sh3/import_mdl.py).
Se reutiliza el direccionamiento ya contrastado del decoder PSMT8 del proyecto.

## Tareas

- [x] **CT-T1 — estructura y vínculos** (CT01/CT02/CT04): sector, tabla,
  descriptores y submallas; fixtures con imágenes distintas y paletas no cero rechazadas,
  referencias inválidas, truncamientos, solapamientos y variantes rechazadas.
- [x] **CT-T2 — píxeles y alfa** (CT03/CT05): reutilizar PSMT8, exportar RGBA
  y previews, comprobar filas, paletas y alfa con oráculo independiente;
  medir cobertura y detectar controles negativos.
- [x] **CT-T3 — adquisición privada** (CT01/CT05): dos lecturas de ISO,
  entregas idénticas, hashes, inspección visual privada, informe de resultados
  y límites; ninguna imagen original en fixtures, repositorio o CI.
- [x] **CT-T4 — material en PCSX2** (CT04/CT05): enlazar actor/submalla con
  TEX0/CLUT y UV/STQ; comprobar TEST/ALPHA/TEX1/CLAMP y semántica de color
  antes de fijar una receta de material 3DS. Usar capturas existentes cuando
  cubran la pregunta y adquirir otras sin reemplazar datos originales.
  - [x] **CT-T4a — atribución** (CT06): verificar hashes de estado/MDL/dump;
    proyectar las 15 submallas y exigir correspondencia STQ única y ordenada.
  - [x] **CT-T4b — estados y selección** (CT07): recorrer los registros GIF,
    identificar contexto, TEX0/CLUT, filtros, clamp, TEST, ALPHA, profundidad,
    máscara de escritura, FBA/PABE, TEXA y niebla; confirmar en replay SW.
  - [x] **CT-T4c — color y transparencia** (CT08): comparar las tres texturas
    efectivas byte a byte, correlacionar los triángulos y comprobar píxeles
    interiores con error RGB máximo 2/255 y alfa máximo 1/255; controles de
    mezcla añadida, inversión V, textura errónea y omisión de modulación.
    No cambiar tolerancias para convertir un fallo en aprobación.
  - [x] **CT-T4d — cierre reproducible** (CT05–CT08): auditor, pruebas
    sintéticas host y receta acotada para CT-T5, con límites explícitos sobre
    iluminación, otras instancias/animaciones y fidelidad física.
- [ ] **CT-T5 — integración y consola** (CT05): conservar particiones por
  material, texturas y UV en un formato versionado; añadir renderer, pruebas,
  build ARM, Azahar y entrega física independiente con costes medidos.
  - [x] **CT-T5a — contrato y paquete**: fijar una nueva versión compatible
    con el visor anterior; conservar UV, tres grupos y selector cero, validar
    índices/rangos/CRC y presupuestos antes de reservar memoria; documentar
    conversión de alfa PS2 al formato GPU sin habilitar mezcla implícita.
  - [x] **CT-T5b — renderer**: aplicar textura por grupo, bilineal y clamp;
    comprobar sentido de profundidad y escritura, mantener mezcla/prueba
    alfa apagadas y declarar iluminación neutra/diagnóstica si aún no existe
    equivalencia de iluminación dinámica del juego.
  - [x] **CT-T5c — regresión y build**: fixtures sintéticos con tres imágenes
    distintas, UV asimétricas, alfa cero y referencias inválidas; pruebas de
    carga, rechazo y ciclo de vida, build ARM reproducible y manifiesto nuevo.
  - [x] **CT-T5d — emulador y entrega**: inspeccionar orientación, vínculos,
    profundidad, cámara y animación en Azahar; preparar un paquete privado y
    comprobar la SD virtual. La copia física se realizará cuando el usuario
    conecte la SD para CT-T5e, con comprobación posterior de hashes.
  - [x] **CT-T5e.1 — consola funcional**: usuario confirma caballo con texturas,
    avance Q12, controles, START, tapa/HOME y 60 segundos sin bloqueo con
    `ced27c955e41`. Evidencia comunicada el 2026-10-22, sin instrumentación.
  - [ ] **CT-T5e.2 — costes físicos**: recoger lecturas Skin CPU, Submit+wait
    y GPU anterior del build corregido durante al menos 60 segundos;
    separar aproximaciones de medidas instrumentadas y registrar build.

CM-T5e.2 conserva la duración y los detalles físicos que falten; no bloquea
CT-T1–T3. Daño/muerte, base mundial definitiva y F03.02 global siguen abiertos.

Evidencia: [ejecución CT-T1–T3](../docs/execution/f03-02-character-materials.md)
y [CT-T4](../docs/execution/f03-02-character-material-runtime.md).
CT-T4 cubre las 15 submallas de una instancia/pose del clip 0x1449: 428 paquetes,
519 triángulos SW y 15.112 píxeles interiores. Confirma ABE=ATE=DATE=0,
MODULATE, bilineal, clamp y profundidad; iluminación dinámica y otras variantes
siguen pendientes. CT-T5 debe preservar ese alcance al presentar el material.

**CT-T5a–d completadas**: [EARS y diseño](../docs/specs/sh3-3ds/character-material-inspection.md),
[informe de integración](../docs/execution/f03-02-character-material-inspection.md).
Build `3fde5682ed11`: **CT-T5e física fallida**, caballo ausente y bloqueo.
[CT-T5f](../docs/execution/f03-02-character-material-gpu-fix.md) completa la
salida del shader y añade un gate del SHBIN; build `ced27c955e41` preparado.
**Repetición funcional CT-T5e.1 aprobada; tiempos CT-T5e.2 pendientes**.
La siguiente investigación es [iluminación LI](ps2-character-lighting-v1.md).
