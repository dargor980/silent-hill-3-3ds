# LI-T1–T3 — Iluminación del caballo en la captura europea

2026-10-22. **Ruta, oráculo y contraste completados para el perfil observado.**
Cuatro poses de `0x0209` / `0x1449`, 500 vértices VU y los 1.712 colores
de 428 paquetes GS coinciden con el cálculo independiente.
[EARS, diseño y tareas LI](../../schemas/ps2-character-lighting-v1.md).

La prueba física del visor neutro **`ced27c955e41`** está aprobada por el
usuario: texturas, Q12, 60 segundos sin bloqueo, controles, START, tapa y
HOME. Los tiempos CT-T5e.2 siguen pendientes. Esta investigación no produce
un build nuevo ni acredita iluminación PS2 en la consola.

## Procedencia y ruta

Se releen los cuatro pares privados CM-T4 (3/4, 5/6, 7/8, 9/10), con entrada
EE `0x001D39BC` y salida `0x001D3A28`. Se verifican hashes de estados, ELF
europeo, MDL, ANM, malla y microprograma, PC, actor `0x0044D950`, instancia
`0x018F`, clip y paletas. Son capturas de una sesión diagnóstica que restauró
una vez al inicio; no se atribuyen a una partida continua nueva. En este
trabajo no se abre ni modifica la VM ni se restauran estados.

Las 15 submallas tienen modo `2` en `+0x40`. La rutina EE `0x001D8AB0`
inicializa color a cero, deforma la malla y llama al constructor de luces
`0x001D79D0`. Los getters `0x001C51C0`, `0x001C51D0` y `0x001C52A0`
leen un contexto con dos direccionales y una luz local de tipo `0x10`.
El grupo direccional adicional solo se emite si el contador alcanza cuatro;
esa rama no se ejerce aquí.

El buffer correcto es el preparado **dentro de la llamada de dibujo**.
`0x001D7230` elige `0x01E57900 + índice*0x800` y avanza un anillo de ocho
entradas. La auditoría deriva el índice desde la captura de entrada y exige
que coincida con el puntero y el índice posterior. Usar el puntero antiguo
provoca errores en los 500 vértices; no se elige el buffer por semejanza de color.
También se cotejan byte a byte los campos de la luz local y su copia al buffer.

| Bloque preparado | Destino / aplicación |
|---|---|
| `+0x2C0`, cuatro vectores | Posición, dirección, RGBA y atenuación de la luz local; MSCAL `0x0C` |
| `+0x00`, diez vectores | Direcciones por columnas, colores direccionales y ambiente; MSCAL `0x0E` |
| Submalla `+0x60` / `+0x70` | Coeficientes RGB difuso y ambiental; el escritor fuerza W=1 |
| `+0x560` | Techo de color de salida `(128,128,128,255)` para clamp y FTOI0 |

El microprograma cargado coincide con el MPG del ELF europeo. Se comprueban
los destinos de las entradas: `0x0C → 0x1D4`, `0x0E → 0x205`, expresados
en instrucciones de ocho bytes. Las ramas `0x08` y `0x0A` existen y sus
destinos también se verifican, pero sus ecuaciones no se dan por validadas.

## Ecuación contrastada

Todos los vectores usan el espacio posterior al skinning. La normal `N`
se conserva sin normalizar. Para la luz local de posición `L`, dirección
`D`, color `S` y atenuación `(a,b,c,d)`:

```text
U = (P - L) / longitud(P - L)
sat(x) = min(1, max(0, x))
local = S * sat(N·U) * sat(a / longitud(P-L) + b) * sat(c*(D·U) + d)
direccional = suma(color_i * max(0, dirección_i·N))
color = material_ambiente * ambiente_escena
        + material_difuso * (local + direccional)
color_GS = truncar(clamp(color, 0, techo_salida))
```

La suma direccional de MSCAL `0x0E` usa tres columnas; el tercer color es
cero en estas capturas. Su producto normal tiene solo límite inferior;
el de la luz local tiene límites inferior y superior. Los coeficientes de
material RGB provienen de la submalla y ambos W valen uno. Por eso alfa no
se reconstruye copiando el alfa de textura ni fijándolo a 255. La posterior
modulación de textura corresponde al oráculo GS ya verificado en CT-T4.

`tools/qa/character_lighting_oracle.py` implementa únicamente este cálculo
puro, en doble precisión, sin acceso a archivos, punteros PS2, GPU o estado
global. Rechaza vectores inválidos, perfiles ajenos, overflow y distancia
singular no verificada. No pretende emular el redondeo ni las latencias VU.
El adaptador privado conserva adquisición y atribución separadas del oráculo.

## Resultados y pruebas

Tolerancia VU fijada antes de aceptar: **0,002 unidades PS2**. Se prueban
tanto posiciones/normales retenidas en VU como las calculadas desde MDL y
paletas por el oráculo de skinning independiente. Los 125 vértices distintos
retenidos pertenecen a las submallas 4 y 5 y se comparan en cuatro poses.

| Q12 | Vértices | Error absoluto máximo RGBA |
|---|---:|---:|
| 67438 | 125 | 0,000061603 |
| 81990 | 125 | 0,000045403 |
| 85676 | 125 | 0,000048054 |
| 89362 | 125 | 0,000037998 |

La última pose permite extender la comparación a **las 15 submallas**:
CT-T4 atribuye cada paquete por STQ de forma única. Tras clamp y truncamiento,
**1.712/1.712 RGBA coinciden exactamente**, en 428 paquetes, sin excepciones.
Son apariciones de vértices en comandos, no 1.712 vértices distintos.

| Control negativo | Muestras VU que superan tolerancia | Error máximo |
|---|---:|---:|
| Usar parámetros del dibujo anterior | 500 | 60,6954 |
| Omitir luz local | 21 | 42,0150 |
| Omitir ambiente | 500 | 124 |
| Normalizar normales deformadas | 313 | 0,786907 |
| Sustituir por luz neutra | 500 | 116,48 |

- 17 tests nuevos y 56 subtests sintéticos; líneas y ramas del oráculo 100 %.
- 210 tests relacionados aprobados: iluminación, skinning, material GS,
  decodificador/paquete de materiales y guardia PICA.
- Ruff y formato aprobados para los dos archivos nuevos.
- El job Python de CI ya descubre `tests/python`; no requiere datos privados
  ni cambios de pipeline. No se ejecutó CI remoto ni se recompiló ARM: el
  renderer y el build físico aceptado no se modificaron en esta tarea.
- Dos auditorías completas producen el mismo informe de metadatos.

Auditor local: `build/character-lighting/audit_lighting.py`.
Informe: `reports/local/f03-02-character-lighting-v1.json`.
SHA-256: `d94ba23252c58a6f79fa8b686c521b4c1e1a9be9583c006e87e3af575b702a0e`.
Copias de evidencia y fuentes de auditoría bajo el directorio privado
`f03-02-character-lighting-v1`; el recibo enumera sus hashes. El repositorio
contiene el oráculo, fixtures sintéticos y esta explicación, sin recursos
originales ni estados de memoria.
SHA-256 de `receipt.json`:
`89aecd896427d9b8b94af8f492eb488c06a0b1359ba6209acbd64ac04503642a`.

## Integración posterior y límites

**LI-T4**: [integración y build b27d16a1671e](f03-02-character-lighting-inspection.md),
con SCL1, pruebas host, build ARM y gate PICA. **LI-T4f.1** aceptada por el
usuario: 60 s por modo, caballo iluminado, SELECT, controles y START/tapa/HOME.
**LI-T4f.2** conserva métricas pendientes («sin medir»). Las luces de esta captura solo
pueden presentarse como un preset de inspección; seleccionar luces dinámicas
entre escenas requiere investigación adicional. No se horneará un color
de vértice de una única pose como sustituto de la ecuación.

Sombras, reflexión, otras luces/modos, descarte VU, base mundial definitiva
y transiciones de daño/muerte permanecen pendientes. F03.02 global sigue abierto.
