# MP01–MP07 — Estructura de mapa y candidato de material PS2

2026-10-20. Instancia preparatoria de F03.02, posterior a TI-T5.
RF02.04/RF02.05/RF02.08 y RNF06.01. Objetivo: obtener rangos verificables de
geometría y campos de material para investigar la muestra de textura.

## Requisitos EARS

- **MP01** WHEN se eligen explícitamente un mapa y una textura THEN el sondeo
  SHALL reconciliar catálogo/recibo fijados por SHA-256 y verificar el conjunto
  privado antes y después; SHALL leer mediante el adaptador de integridad.
- **MP02** WHEN se recorre el mapa THEN el parser SHALL comprobar límites de
  cabeceras, cadenas, contención padre/hijo y presupuesto antes de leer;
  SHALL admitir raíces que comparten una cola sin duplicar grupos.
- **MP03** IF hay truncamiento, ciclo, solapamiento, contador discordante o
  rango de vértices inválido THEN SHALL rechazar la instancia completa con
  código estable; no se publicará una estructura parcial como aceptada.
- **MP04** WHEN se registran campos de grupo, malla o forma THEN SHALL
  conservar valores, offsets y hashes de cabecera; SHALL mantener sin validar
  la selección de textura/paleta, UV, transformaciones y semántica de flags.
- **MP05** WHEN dos nombres tienen raíz común THEN SHALL registrarse solo una
  pista no verificada; SHALL NOT declarar una relación material/textura,
  habitación o uso en PS2 por coincidencia de nombre o índice.
- **MP06** WHEN se produce evidencia THEN SHALL contener solo metadatos,
  sin vértices, píxeles ni nombres privados; SHALL publicarse exclusivamente
  tras cerrar el lector y rechazar un destino existente.
- **MP07** WHEN se acepta esta instancia THEN SHALL pasar fixtures propios
  y dos lecturas idénticas del mapa seleccionado; SHALL distinguir estructura
  de geometría decodificada, visualización y comparación dinámica con PS2.

## Diseño y subconjunto

Parser puro `map_probe.py`, puerto `read(offset, length) -> bytes`; coordinador
`map_survey.py`; adaptador `VerifiedPrivateReader` y publicación existentes.
Sin dependencias 3DS/Blender/Noesis. CI descubre los tests sintéticos Python.

Referencias públicas leídas, sin ejecutar sus plugins:

- [Sparagas, parser MAP](https://github.com/Sparagas/Silent-Hill/blob/f08ec73e32c0b0d5ddbb58f96eef51f0b8ee5b35/Noesis%20-%20Python%20Plugins/fmt_sh3_ps2_map.py)
  y [plantilla](https://github.com/Sparagas/Silent-Hill/blob/f08ec73e32c0b0d5ddbb58f96eef51f0b8ee5b35/010%20Editor%20-%20Binary%20Templates/sh3_map_ps2.bt),
  revisión `f08ec73e32c0b0d5ddbb58f96eef51f0b8ee5b35`, MIT.
- [Murugo, importador MAP](https://github.com/Murugo/Misc-Game-Research/blob/f25bbc59c3dbbe318a09419beb17d01407c75277/PS2/Silent%20Hill%202%2B3/Blender/addons/io_sh2_sh3/import_map.py),
  revisión `f25bbc59c3dbbe318a09419beb17d01407c75277`, MIT.
  Usa offsets relativos de contenido; su material es genérico, sin resolver
  asignación de textura. El parser Sparagas tampoco asigna materiales.

Todos los enteros son little-endian. Presupuesto de esta herramienta: 32 MiB,
8192 nodos únicos, 2.000.000 vértices declarados. No son límites del juego.

| Elemento | Subconjunto observado / validación |
|---|---|
| Área | 48 bytes, magic `0xFFFFFFFF`; raíces u32 en 28/32/36. Los demás campos se conservan opacos. Una raíz cero se omite. |
| Nodo | `next`, `data_delta`, `total_size`, opaco: cuatro u32. `next` absoluto; contenido relativo al inicio. Offsets/tamaños múltiplos de 16. Cabecera y contenido dentro del padre. |
| Cadenas | Terminación cero, avance hacia delante sin solapar hermanos. Grupos compartidos entre raíces se leen una sola vez; raíces dentro de otro grupo se rechazan. |
| Grupo, 48 bytes | u32 en 16/20 opacos, u16 en 24 contador de mallas, resto opaco. Contador igual al recorrido. |
| Malla, 48 bytes | u16 en 16 candidato CLUT; u16 en 18/20/22 opacos (22 es flag candidato). No decide paleta ni alpha. |
| Submalla, 48 bytes | Campos restantes opacos. |
| Forma, 64 bytes | u32 en 16 cantidad de vértices; u32 en 20 índice de transformación opaco. Rango de `cantidad * 16` dentro del nodo; longitud restante documentada. |
| Datos no recorridos | Matrices, bounding boxes, payloads y posible sección de texturas quedan sin interpretar; no se declara consumo completo del MAP. |

El reporte conserva jerarquía, raíces y nodos únicos, resumen y rangos.
La textura se sondea con TEX01–TEX07. Un `--embedded-offset` opcional permite
contrastar una hipótesis de área de texturas al final del MAP: debe ser múltiplo
de 16, estar después de todos los grupos y consumir exactamente el resto del
archivo con el parser TEX. Sus offsets se declaran relativos a esa área.
No se descubre automáticamente a partir de un campo todavía opaco.
Ambos IDs se solicitan explícitamente;
compartir contenedor o raíz de nombre no crea un vínculo material.

## Tareas

- [x] **MP-T1:** parser y pruebas de raíces compartidas, rangos, contadores,
  presupuesto y lecturas inválidas. MP02–MP04.
- [x] **MP-T2:** CLI con par explícito, integridad, salida exclusiva y pruebas
  de corrupción/selección/fallos de lectura. MP01/05/06.
- [x] **MP-T3:** contrastar dos copias, fijar referencias y documentar el
  candidato menor para investigación de geometría/material. MP07.
- [x] **MP-T4:** demostrar la relación con textura y paleta mediante cargador
  PS2 o captura de dibujo identificada; comparar el uso en escena.
  Dependencia posterior: los índices/nombres solos no cumplen este criterio.
  [MR-T4b/c](../docs/execution/f03-02-map-runtime-binding.md) identifican
  recurso, banco y CLUT 0; [MR-T4d](../docs/execution/f03-02-map-draw-state.md)
  demuestra el consumo GS y transparencia de ambas formas con cámara de
  inspección. No acredita una partida normal del hospital.

[Ejecución y resultados](../docs/execution/f03-02-map-material-candidate.md):
233 pruebas, informes iguales de ambas copias y grupo candidato de 56 vértices.
