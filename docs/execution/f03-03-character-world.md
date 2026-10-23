# GC-T4 — Del personaje deformado al espacio mundo

2026-10-23. **GC-T4a–c completadas para `0x0209` / `0x1449`**, edición
europea SLES-51434. [EARS GC07–GC11 y tareas](../specs/sh3-3ds/character-world-conventions.md).
Se cierra la definición matemática de este perfil, con límites numéricos
explícitos. La colocación en un visor nuevo queda en GC-T5; no se generó
otro build ni se modificó el visor físico `b27d16a1671e`.

## Construcción y consumo de instancia

Se leyeron los 28 estados 08–35 de la sesión continua ya auditada, sin abrir
PCSX2, restaurar estados ni escribir en RAM invitada. Sus SHA-256 se contrastan
con el informe fijado de SA-T5d, además de recibos, PC, registros e identidad.
Cada estado contiene tres actores activos `0x0209`: instancias `0x18e`,
`0x18f` y `0x190`, en `0x44d630`, `0x44d950` y `0x44dc70`.
Son **84 observaciones**, con 28 posiciones diferentes por instancia.

| Campo de actor | Interpretación verificada en este perfil |
|---|---|
| `+0x14/+0x18/+0x1c` | Escala por columna; `(1,1,1)` en los 84 casos |
| `+0x20` | Posición `(x,y,z,1)` en unidades originales |
| `+0x30` | Giro; solo Y distinto de cero en la muestra |
| `+0x40` | Matriz modelo → mundo, 16 f32 por columnas |
| `+0x70/+0x74/+0x78` | Traslación de esa matriz, idéntica a `+0x20..+0x28` |

El recorrido `0x1dcaf0` llama a `0x1dcba0` con actor, giro `+0x30` y posición
`+0x20`. El constructor pasa los componentes X/Z a `0x1213a8`, aplica Y mediante
`0x121300`, escribe traslación y W=1, y llama a `0x1dcb40` para escalar las
tres columnas. Estas ventanas se cotejaron byte a byte entre ELF europeo y
todos los estados usados. No se reconstruye un orden Euler general a partir
de giros X/Z nulos.

Para la muestra se verifica `M=T(p)*Ry(yaw)`, con columnas
`(cos,0,-sin,0)`, `(0,1,0,0)`, `(sin,0,cos,0)`, `(px,py,pz,1)`.
Error máximo frente a `sin/cos` host: **1,35837e-7**, bajo 1e-6; traslación
y fila afín exactas. El constructor original admite escala, pero este contrato
público acepta únicamente instancias rígidas propias observadas.

El consumidor CM pasa `actor+0x40` a `0x1d3920`; prepara `View*M`, sustituye
su fila W por Z y compone pose y helpers para VU. La sustitución W=Z pertenece
al consumidor proyectado; **no es la W del personaje en mundo**.

## Convención y separación de responsabilidades

El módulo puro `tools/pipeline/character_space.py` aplica una instancia rígida
a una posición4 y una normal3 ya deformadas. La posición conserva W; la normal
no recibe traslación ni se normaliza. Rechaza reflexión, proyección, escala,
cizalla, entradas inválidas, magnitudes fuera del perfil y resultados no finitos.
Conserva copia inmutable de las columnas y no depende de oráculos QA, archivos,
SDK ni actores del juego.

`world = M * blend(P_i * H_i * local)` aplica M una vez, después de la pose.
Los helpers almacenados conservan autoridad; la influencia primaria usa
identidad. Pesos Q12 deficientes no se renormalizan. La normal usa únicamente
las partes lineales de esos productos.

`B=diag(1,-1,-1,1)` se aplica después de M. Si el dato local ya cambió de base,
su instancia es `B*M*B^-1`; ambas rutas dan el mismo resultado. B conserva W
y orientación (determinante +1). Centrado, escala de presentación, cámara y
unidades físicas siguen separados. No se fija una equivalencia con metros.

## Contraste numérico y controles negativos

Se releyeron los cuatro pares CM 03/04, 05/06, 07/08 y 09/10, vinculados por
hash al informe CM-T4. Esa sesión era una reproducción diagnóstica con una
restauración inicial, distinta de la sesión continua SA. Pose, matrices,
recursos, PC, registros, ventanas de código y estabilidad entre entradas/salidas
fueron comprobados. Se comparan **500 muestras / 125 vértices distintos** de
las submallas 4 y 5; no son todos los vértices ni todos los dibujos del actor.

| Contraste | Error máximo | Interpretación |
|---|---:|---|
| Ruta mundo y ruta compuesta, posiciones en doble | 1,31877e-11 | Equivalencia algebraica; límite 1e-8 |
| Mismas rutas, normales en doble | 3,33067e-16 | Equivalencia algebraica; límite 1e-12 |
| Paleta preparada PS2 → posiciones VU | 0,000831400 | Pasa el límite CM de 0,001 |
| Paleta preparada PS2 → normales VU | 2,13630e-7 | Pasa el límite CM de 1e-5 |
| Cálculo separado en mundo → posiciones VU | 0,009027917 | **500/500 fuera del límite CM de 0,001** |
| Cálculo separado en mundo → normales VU | 4,01875e-7 | Diferencia medida, no emulación completa |

No se amplió ninguna tolerancia CM. La ruta en doble cambia la preparación
y el orden de operaciones respecto de EE/VU. Reproducir la preparación de
matrices con redondeo hacia cero y usar la paleta capturada mantiene los
límites anteriores; esto no convierte el módulo de mundo en un emulador
numérico. **GC-T5 deberá fijar y verificar su presupuesto de colocación antes
de presentar equivalencia de render**. El preset LI continúa usando su
transformación capturada, por lo que esta diferencia no cambia el build aceptado.

Los controles incorrectos se detectan en datos reales: modelo duplicado,
500/500; base antes del modelo, 500/500; W forzado a 1, 128/128 muestras con
pesos deficientes (desviación máxima **49,3157 unidades**). El fixture público
añade rotación transpuesta, división por W, normalización indebida y orientación
de tetraedro asimétrico, sin datos propietarios.

## Pruebas, pipeline y evidencia

- **246 pruebas y 56 subtests aprobados**, incluidas 45 pruebas nuevas;
  regresiones de convenciones MAP, skinning, pose, continuidad e iluminación.
- Módulo nuevo: **43/43 líneas y 14/14 ramas**, 100 %.
- Ruff, formato y contratos del repositorio aprobados.
- El job `quality` ya descubre el nuevo módulo/tests y ejecuta cobertura;
  no necesita ISO ni estados privados. No se ejecutó CI remoto ni un nuevo
  build ARM, pues no cambió el código del visor en esta tarea.

```sh
rtk proxy .venv/bin/python -m pytest \
  tests/python/test_character_space.py tests/python/test_geometry_conventions.py \
  tests/python/test_character_skinning_oracle.py tests/python/test_animation_pose_oracle.py \
  tests/python/test_animation_continuity.py tests/python/test_character_lighting_oracle.py \
  tests/python/test_character_lighting_inspection.py \
  --cov=tools.pipeline.character_space --cov-report=term-missing \
  --cov-report=json:build/character-space-coverage.json \
  --junitxml=build/character-space-pytest.xml -q
rtk proxy .venv/bin/python build/character-space/audit.py
rtk proxy .venv/bin/python -m tools.qa.coverage_gate build/character-space-coverage.json
rtk proxy .venv/bin/python -m tools.qa.check_repository
```

Auditor local `build/character-space/audit.py`, SHA-256
`f9b34ef131e33c35134c06e507bfb1b95f44b2844ce9758bd5adbcca3237a70f`.
Informe local `reports/local/f03-03-character-world-v1.json`, SHA-256
`b7294bb86f2458baf9d9e86e334d5a0aca523ad92e3b50c23559c78a6c147ca4`.
Fuentes fijadas: continuidad
`ea78b9d400712f07616794b0382da196bf5a9bb57b55d53c9002109a9914163c`
y CM `a4b6c2cc8fdd08fced7fc679a9aaf6e9d41ec0a1bd998a2a2b688e9ae992fbe0`.
Estados y malla permanecen en el directorio privado externo; el informe local
no forma parte de los artefactos CI.

## Cobertura acumulada y siguiente tarea

[SA](f03-02-skeleton-runtime.md) fija bosque de tres huesos, raíces
independientes, pose modelo, NLERP y reloj Q12;
[SA-T5d](f03-02-animation-continuity.md) verifica la vuelta continua;
[CM-T4](f03-02-character-runtime.md) verifica matrices, helpers y pesos;
GC-T4 añade instancia mundo y base de inspección. No se deduce movimiento de
raíz desde las oscilaciones de posición de los actores.

**Siguiente: GC-T5**, contrato y visor de colocación de instancias en mundo,
con selección explícita de política numérica y luz de inspección; después,
build y prueba física propios. Daño/muerte, mezclas, giros/escala no observados,
selección de luces de escena y circuito jugable siguen pendientes. F03.03
global y G02/G03 permanecen abiertos. LI-T4f.2 queda «sin medir».
