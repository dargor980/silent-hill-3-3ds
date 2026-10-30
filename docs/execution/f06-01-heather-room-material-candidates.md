# HM-T4c.3.1 — Inventario candidato de materiales originales

2026-10-30. **HM-T4c.3.1 completada** conforme a
[HRM01–HRM07](../../schemas/heather-room-material-candidates-v1.md).
El usuario aplaza las comprobaciones físicas restantes de HM-T5 y solicita
continuar con otras tareas. Se conserva el build funcional `161090bc9fd5`.
Esta entrega es una herramienta host y evidencia de datos; no cambia el
renderer, el paquete SD ni la aceptación física anterior.

## Inventario y correspondencia candidata

Se autentican catálogo, recibo de extracción, recursos A/B y ambos paquetes
originales de Heather. Los grupos se recorren por los contadores de sus raíces,
sin duplicar la cola estructural compartida. El MAP contiene ocho grupos,
diez mallas y 31 formas. Un bloque externo de 256×256 y siete internos de
512×512 contienen 44 variantes de paleta, todas PSMT8.

La hipótesis explícita relaciona el grupo externo `(2,0)` con el bloque
externo 0 y cada grupo interno `(3,n)` con el bloque interno `n-1`. Se exige
la secuencia completa, sin huecos ni duplicados. No se emplea `texture_id`
como clave: todos esos campos valen -1 en estos recursos.

| Grupo MAP | Bloque candidato | Selectores candidatos | Formas |
| ---: | --- | --- | ---: |
| 304 | Externo 0 | 0 | 2 |
| 1472 | Interno 0 | 0 | 4 |
| 130224 | Interno 1 | 0 / 1 | 5 / 2 |
| 159136 | Interno 2 | 0 | 5 |
| 226320 | Interno 3 | 0 | 2 |
| 232640 | Interno 4 | 0 / 14 | 5 / 2 |
| 247696 | Interno 5 | 0 | 2 |
| 253792 | Interno 6 | 0 | 2 |

Son **nueve combinaciones internas y una externa**. Las dos formas de vidrio
conservan su prueba histórica, pero la nueva tabla no se presenta como prueba
de asociación original de las restantes. Cada registro mantiene offsets,
campos opacos y hashes. El informe declara `material_binding=unverified`,
`runtime_comparison=pending` y `capabilities=[]`.

El selector CSM1 no equivale al ordinal de una paleta horizontal: una carga
de cuatro unidades admite `0,1,4,5`. El selector 14 del bloque de dieciséis
unidades está dentro del subconjunto ya soportado por `ps2_indexed`.
No se modificó ese decodificador ni se reinterpretó alpha para aceptar datos.

## Píxeles y presupuesto

El oráculo separado reconstruye direcciones de memoria GS: carga PSMCT32,
lectura PSMT8 y CLUT CSM1. Utiliza tablas primarias de PCSX2, revisión
`fd9d310ccbb6b8b62c976da8886a3c8fd3a10ff3`, archivo local `GSTables.cpp`,
SHA-256 `a9a226297ede32b89177d7bdb04e9d8e21728e7d55799405f6112e97fe4969e8`.
No llama a las fórmulas de dirección ni al decodificador del pipeline.

Por copia coinciden los índices de ocho bloques, 44 paletas y todos los
RGBA de **10 747 904 píxeles**; entre A/B, **21 495 808 píxeles** comparados.
Se preserva alpha PS2 en 0..128, sin normalización. El selector 1 del interno
1 contiene alpha binario 0/128; el selector 14 del interno 4 tiene alpha
entre 0 y 120. Esto exige verificar TEST/ALPHA y escritura de profundidad;
los valores de textura por sí solos no demuestran descarte ni mezcla.

| Escenario RGBA sin compresión | Memoria de texturas |
| --- | ---: |
| Todas las variantes del mapa | 41 MiB |
| Todas las variantes + Heather | 58.25 MiB |
| Diez combinaciones candidatas del mapa | 9.25 MiB |
| Diez combinaciones + Heather | **26.5 MiB** |
| Límite residente del proyecto | 32 MiB |
| Mayor imagen candidata / staging | 1 MiB |

La deduplicación compara contenido exacto y dimensiones: estas diez imágenes
son distintas. El ahorro viene de seleccionar variantes en lugar de expandir
todas las declaradas. Se conserva la prueba sintética de contenido idéntico
con dimensiones diferentes, que no debe deduplicarse. Estas cifras no incluyen
una nueva integración runtime ni son mediciones de RAM física de consola.

## Implementación y verificación

`tools/inspectors/map_material_candidates.py` es puro: recibe bytes y el offset
explícito de la sección, valida y devuelve únicamente metadatos. Reutiliza los
lectores MAP/TEX y el decodificador existente. Rechaza raíces ajenas al perfil,
secciones solapadas, índices de grupo discordantes, formatos distintos, selectores
inválidos y presupuestos excedidos antes de publicar resultados.

`tests/heather_room_material_candidates_audit.py` autentica las fuentes,
reconcilia A/B, ejecuta el modelo GS separado y relee 40 fuentes al terminar.
El informe es exclusivo, con permisos 0600 y lectura posterior. No genera
imágenes, recursos intermedios ni payloads de juego dentro del repositorio.

- Fallo inicial con el inspector sin implementar conservado en
  `build/heather-room/material-candidates-v1/red.log`.
- **353 pruebas** de regresión aprobadas, incluidas las primeras 22 del inspector.
- Tras ampliar los casos: **28/28 pruebas del inspector**, con alpha 0/64/255,
  selectores 4/5/14 y deduplicación por dimensiones/contenido.
- Cobertura del módulo: **67/67 líneas y 20/20 ramas, 100 %**.
- Auditorías normal y `python -O` exactamente idénticas: 49 917 bytes,
  SHA-256 `959ea2a0861120936b135a30416c57649c23c4d4844b294f1e12ee2e53ff7719`.
- Ruff incorpora el auditor privado en CI; los fixtures sintéticos se descubren
  en el job Python existente. No se atribuye ejecución de CI remoto.

Informes: `reports/local/heather-room-material-candidates-v1.json` y
`reports/local/heather-room-material-candidates-v1-optimized.json`.
JUnit/cobertura: `build/heather-room/material-candidates-v1/`.
No se recompiló ARM: esta fase no cambia código de consola.

## Continuación

**HM-T4c.3.2 completada:** véase la [verificación original](f06-01-heather-room-material-binding.md).
El alcance previsto era contrastar el selector de banco interno y de CLUT con el
consumidor europeo y capturas del dibujo; verificar TEX0/CLAMP, TEST/ALPHA,
ZBUF, visibilidad y tratamiento de color/niebla de las 29 formas. La hipótesis
numérica y el cotejo de píxeles no sustituyen esa evidencia.

**HM-T4c.3.3:** integrar solo materiales demostrados, conservar geometría y
controles, recalcular memoria total y preparar un build host/ARM identificado.
HM-T5 continúa aplazado, sin perder sus observaciones previas.
