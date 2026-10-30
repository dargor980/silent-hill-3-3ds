# HM-T2b.6: aproximación a la pared 60

**En curso.** Se definió un punto de espera P = **X −28950, Z 19450** y
una ruta exterior con separación geométrica contrastada. Su llegada por
controles normales sigue pendiente. La referencia estática parte de C137;
los intentos posteriores y sus límites se conservan por separado.
No hay nueva grabación, restauración, parche de posición ni build de consola.

## Referencia estática

El recurso `tpf1.cld` completo coincide entre A/B y RAM: SHA-256
`8263496d10c74c085a01a480d089c9fc5912b071a4f4f1d39c88ed31269461b6`.
Se examinan las cuatro listas poligonales, 273 paredes que intersectan la
banda Y capturada, 152 registros no verticales y los ocho cilindros.
El decoder y su oráculo mantienen `CP_NONPOLYGON_UNSUPPORTED` para el
recurso mixto; esta investigación no amplía el contrato de producción.

La ruta propuesta desde C137 pasa por `(X inicial, 21100)`,
`(−29200, 21100)`, `(−29200, 19700)` y P. El cálculo usa distancias
continuas entre segmentos con fracciones exactas, no muestras espaciadas.
Las separaciones mínimas de sus tramos son 174,943359375; 450; 303,75 y
223,60679775. La primera conserva un déficit inicial de 0,056640625 frente
a 175 y se aleja monótonamente de la pared 4. **175 es el valor observado
en las dos consultas de C137; no se generaliza como radio universal.**
La superficie de suelo 5 del grupo 0 contiene la ruta y el punto de sondeo;
su Y es 0,1153300032. Las otras comprobaciones se limitan a la banda Y
capturada; no certifican selección dinámica de suelo ni ausencia de actores.

P queda fuera del contacto según esa referencia. El sondeo posterior
T = `(−28950, 19370)` alcanza la vecindad del extremo occidental de la
pared 60, compartido con la **pared 24**, no con la 14. La normal nativa
de 60 es +Z; se contrasta con el plano guardado y no se sustituye por el
sentido contrario del helper geométrico.

El hueco 14/60 mide 116,701171875. Las prolongaciones perpendiculares 12/13
ocupan 1026,599609375 en Z y las superficies 98–100 del grupo 2 están entre
ellas. No es un pasillo vacío demostrado. Bajo el modelo condicional de
separación 175, las franjas exteriores despejadas quedan a al menos
291,701171875 de la pared opuesta: esta cota local no demuestra
inaccesibilidad global ni cierra el contacto simultáneo.

Informe local: `reports/local/heather-movement-wall60-access-v1.json`, SHA-256
`2b0609659ecb01fd3829b30d18de56bb9967e2b042da7ba87ae2be528534285e`.
El croquis `build/heather-movement/wall60-access-C137.png` representa C137,
no la posición actual. Recursos, estados e imagen quedan locales.

## Intentos manuales y guía por etapas

C138 conserva X/Z de C137: el usuario no pudo identificar la ruta y pausó.
C139 queda en X −18963,47265625, Z 20369,427734375. El usuario confirma que
solo caminó con las flechas, sin puerta ni cambio de zona. Entre ambas
capturas hay 440 actualizaciones y 881 fotogramas nativos; el desplazamiento
es +9482,79296875 en X y −1005,62890625 en Z. Los controles no se grabaron:
los extremos no reconstruyen la trayectoria, velocidad ni duración de pulsación.
Ninguna captura alcanzó P ni el límite de actualizaciones del primer filtro.

Se reabrieron los estados completos para contrastar RAM, CPU, ciclo,
recursos, posición, matriz y consultas. El informe
`reports/local/heather-movement-wall60-access-attempt-v1.json` tiene SHA-256
`5a4f466fb7a7b5222543e55e3b830dbf312536e6fa39e98f42f42e0d3ef0c74e`.
El resultado `passed` acredita preservación y clasificación, no llegada.

Desde C139 se prepararon 95 filas, con tres condiciones por posición,
orientación y botón; las demás quedan en `0`. Archivo y respaldo coinciden:
SHA-256 `8fb963238369f8cc32e26ebfb85ff49d1bed0afa63b3046fb3f43b19ceca3318`.
El usuario cargó los ajustes. La interfaz permitió leer íntegramente las
condiciones de `001DD3F0` y `001DD434`; la tercera (`001DD404`) quedó
visible parcialmente. No se presume verificación completa de esa fila.
El límite de esta guía es el ordinal 115554. La separación de paredes de
la ruta nominal desde C139 se recalculó; no acredita el recorrido real.

Cada giro o caminata requiere comprobar la pausa antes de pedir el tramo
siguiente. Si Space vuelve a parar en el mismo PC antes de leer la nueva
entrada, se conserva esa repetición y se usa un paso del depurador para
salir del punto. Es navegación interrumpida por diagnóstico, no una
reproducción grabada ni evidencia de continuidad temporal sin intervención.

## Capturas de la guía inicial

| Captura | Ordinal | PC | Resultado |
| --- | ---: | --- | --- |
| C140 | 109572 | `001DD3F0` | Giro con ← a yaw 0,03721553; posición de C139 intacta. |
| C141 | 109572 | `001DD3F0` | Repite RAM/CPU/ciclo de C140; no constituye avance. |
| C142 | 109600 | `001DD434` | ↑ hasta X −18937,38671875, Z 21068,927734375; matriz publicada. |
| C143 | 109618 | `001DD3F0` | Giro con ← a yaw −1,54678404; posición de C142 intacta. |
| C144 | 110519 | `00081FC0` | Pausa manual ante barrera; X −28446,2578125, Z 21375,044921875. |

Tras C141 y C143, un «Paso a paso por» sale de `001DD3F0` a
`001DD3F8`; tras C142, sale de `001DD434` a `001DD448`. Los destinos
se observaron en la interfaz. No son capturas adicionales ni una prueba
de continuidad sin pasos de depurador. C141 tiene otro hash de archivo,
pero su RAM completa, registros decodificados y ciclo coinciden con C140.

C144 no alcanza el control occidental X ≤ −29150. La pared vertical más
cercana, grupo 3/índice 4, está a 174,955078125 en X/Z. Esta proximidad no
identifica por sí sola el escritor que impide el avance. El usuario reportó
una barrera y la imagen muestra la reja; se conserva el resultado fallido.
El informe `reports/local/heather-movement-wall60-guidance-v1.json` tiene
SHA-256 `76fd9b6b7feb42b1844ed143f2230107a5b537f4932b194754b8d896b36e2688`.

Se preparó un ajuste desde C144 para girar una actualización normal hacia
el interior del pasillo (yaw entre −1,70 y −1,62), antes de volver a caminar.
La referencia nominal se aleja de la pared 4 y conserva explícito el déficit
inicial de separación de 0,044921875. El archivo respaldado tiene SHA-256
`952eff2e07ea8f9656308cec6a2c53729e2000be19c44ab0119a718470774546`,
95 filas y tres condiciones, con límite en ordinal 113519. El usuario cargó
el ajuste; sus tres condiciones activas fueron leídas en la interfaz, cuyo
inventario parcial expuso 93 filas. C145 registra una sola actualización de
giro con ←: yaw −1,63478398 y X/Z sin cambios. Después se observó el paso
`001DD3F0 → 001DD3F8` para evitar otra pausa repetida.

C146 quedó en pausa manual, ordinal 110669, X −27203,890625,
Z 20773,689453125 y yaw 1,74440348. No alcanzó el control occidental ni P.
El usuario confirmó que también utilizó ←/→ durante el tramo: **no se
considera una prueba de caminar recto ni un giro automático del juego**.
La entrada final `0x1000` no reconstruye los botones anteriores. Ambas
capturas completas pasan la auditoría normal y `-O`, con informe local
`reports/local/heather-movement-wall60-guidance-v2.json`, SHA-256
`c27534755b7542b55b7ccceb144ad4a8c3c9f83c147d53b4954511ada4427fde`.

Se preparó el regreso desde C146, sin reanudar, con 95 filas y tres
condiciones; las demás permanecen en `0`. Su archivo y respaldo tienen
SHA-256 `7f4ececab60e7fb5b735773ee27231b60121d519551325b5883599822ed41152`.
Primero se propone alejarse de la pared 130 hacia Z ≥ 21150 y después
orientarse ligeramente al norte del oeste. La referencia de paredes
conserva el déficit inicial frente a 175; el primer tramo se aleja de ella.
El límite de la guía es el ordinal 112169. El usuario cargó el archivo y
se leyeron completas las tres condiciones activas en la interfaz.
C147 confirma el giro a yaw 0,07240301, ordinal 110688, sin cambio de X/Z.
C148 alcanza X −27175,49609375, Z 21164,638671875, ordinal 110705,
con ↑ y la misma orientación; su matriz publica la posición. Ambos estados
pasan el cotejo independiente normal y `-O`. Informe parcial
`reports/local/heather-movement-wall60-guidance-C148-v1.json`, SHA-256
`0bf00f6cd3c3f7ae67a7d894b5a36083b886febaaa1f121780c0dae8e7171965`.
El indicador de llegada permanece falso.

Se observó «Paso a paso por» desde `001DD3F0` a `001DD3F8` tras C147 y
desde `001DD434` a `001DD448` tras C148. La sesión quedó pausada después
de ese último paso, a la espera del giro occidental solicitado. El resto
del regreso y la llegada a P siguen pendientes.
Cada instrucción se emite tras comprobar la captura anterior; ante una
barrera se pausa antes de decidir otro giro.


## Validación y siguiente paso

Las distancias y contención tienen **23 pruebas sintéticas aprobadas**.
Los auditores de referencia, intentos y guía inicial producen informes idénticos
en ejecución normal y con `-O`. La comprobación del repositorio termina
con cero errores y `git diff --check` no informa problemas. Comandos del trabajo local:

```sh
rtk proxy .venv/bin/python -m pytest build/heather-movement/test_approach_geometry.py -q
rtk proxy .venv/bin/python build/heather-movement/audit_wall60_access.py /tmp/hm-wall60-access.json
rtk proxy .venv/bin/python -O build/heather-movement/audit_wall60_access.py /tmp/hm-wall60-access-optimized.json
rtk proxy .venv/bin/python build/heather-movement/audit_wall60_access_attempt.py /tmp/hm-wall60-access-attempt.json
rtk proxy .venv/bin/python -O build/heather-movement/audit_wall60_access_attempt.py /tmp/hm-wall60-access-attempt-optimized.json
rtk proxy .venv/bin/python build/heather-movement/audit_wall60_guidance_v1.py /tmp/hm-wall60-guidance-v1.json
rtk proxy .venv/bin/python -O build/heather-movement/audit_wall60_guidance_v1.py /tmp/hm-wall60-guidance-v1-optimized.json
rtk proxy .venv/bin/python build/heather-movement/audit_wall60_guidance_v2.py /tmp/hm-wall60-guidance-v2.json
rtk proxy .venv/bin/python -O build/heather-movement/audit_wall60_guidance_v2.py /tmp/hm-wall60-guidance-v2-optimized.json
rtk proxy .venv/bin/python build/heather-movement/audit_wall60_guidance_v3.py 148 /tmp/hm-wall60-guidance-v3-progress.json
rtk proxy .venv/bin/python -O build/heather-movement/audit_wall60_guidance_v3.py 148 /tmp/hm-wall60-guidance-v3-progress-optimized.json
```

**Actualización 2026-10-29:** el usuario solicita saltar esta parte y avanzar
con los datos existentes. Se cancela la instrucción pendiente de girar a la
izquierda; no se pide otro recorrido ni se considera alcanzado P. C148 sigue
siendo la última captura, y la última acción registrada es el paso hasta
`001DD448`; esta decisión no restaura ni reanuda PCSX2.

La aceptación de 60 cerca de 24, contacto simultáneo 14/60 y sus descartes
quedan pospuestos. HM-T2b.6 continúa abierta y sus evidencias se conservan.
El siguiente trabajo es el [perfil nativo HMN v1](../../schemas/heather-movement-native-v1.md),
con contacto separado y límites explícitos; no usa esta geometría auxiliar
como prueba de una ley física ni cierra la habitación HM-T4.
