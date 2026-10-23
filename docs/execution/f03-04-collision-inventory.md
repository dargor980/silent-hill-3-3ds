# F03.04 / IR-T7a–b — Inventario y contrato de colisión

2026-10-23. **Inventario de evidencias y definición del perfil completados.**
[Contrato EARS IR19–IR27 y tareas IR-T7](../../schemas/collision-intermediate-v1.md).
El convertidor no está implementado y no se ha generado otro build 3DS.

## Resultado y elección del perfil

La evidencia disponible permite conservar y reconstruir **registros de
colisión observados en RAM**. No hay todavía un decoder validado de polígonos
o volúmenes de colisión del escenario. Se define `ps2-collision-registry-v1`
con dos bancos de personajes, dos bancos de punteros del escenario, lista
de actores y almacenamiento de eventos, sin confundir sus funciones.

Se releen **30 estados y 30 recibos**, se comprueban hashes y registros contra
el informe anterior y se contrastan **43 ventanas distintas de código/datos**
con el ELF europeo. Las 13 ventanas del informe de colisión se comparan con
RAM en las 30 capturas; las adicionales de rutas alternativas se contrastan
en 08, 35 y 36, respetando el alcance histórico. El texto del overlay se
compara en todas. No se ejecuta PCSX2 ni se modifica memoria o evidencia previa.

## Inventario verificado

| Evidencia | Resultado revalidado | Límite |
|---|---|---|
| SC-T3b.1, registros de colisión | 30 capturas: control 02, 28 muestras 08–35 y diagnóstico 36. Campos de ambos bancos coinciden con el informe. | Inscripción y procedencia; no respuesta física ni todos los instantes entre muestras. |
| SC-T3b.2, rutas alternativas | Informe fijado, ELF/overlay y sus ventanas de código/datos en 08/35/36 conservados. | La investigación histórica no identificó una vía normal de daño; no es una prueba universal de invulnerabilidad. |
| SA-T5d, continuidad | Hash, slots, estados y ciclos del segmento 08–35 coinciden. | Acredita aquel segmento de animación; no continuidad de una trayectoria física de colisión. |
| F02.07, inventarios A/B | Ambos JSON conservan el mismo SHA-256; 285 recursos con indicio de nombre `.cld`. | Son candidatos sin formato ni enlace semántico. Sus payloads no se revalidaron ni decodificaron en esta tarea. |
| Perfil visual IR-T6 | Su alcance documentado es geometría/material de dos paneles. | No demuestra correspondencia con las listas de colisión del carrusel ni sustituye un recurso físico. |

Los informes antiguos conservan ocho controles negativos de colisión y cuatro
de rutas alternativas. Esta tarea verifica sus hashes y las fuentes descritas;
no presenta esos controles históricos como una batería nueva ni reejecuta
una prueba de impacto.

### Separación de fases y propietarios

| Capturas | Sala | Personajes por banco | Escenario por banco | Interpretación admitida |
|---|---|---|---|---|
| 02 | `0xEA` | 23: Heather y dos entradas por cada uno de once `0x020C` | Una lista | Control positivo de inscripción. |
| 08–35 | `0xEB` | Dos: Heather y Alessa | Doce listas | Los tres `0x0209` no figuran como propietarios de personaje; sus posiciones sí tienen listas de escenario registradas. |
| 36 | `0xEB` | Las mismas dos clases | Doce listas | Diagnóstico tras restauración, separado del segmento continuo. |

Todos los puntos observados tienen contador de eventos cero. El contenido
residual del almacenamiento de eventos no se interpreta como entradas activas.
Se preservan las limitaciones de la partida importada, cuyo historial previo
es desconocido. No se solicita repetir golpes o el acertijo.

### Datos conocidos y campos opacos

**Conocidos para el perfil europeo fijado:** direcciones/strides y capacidades
de registros, selectores, contadores, propietario, palabras de presencia,
callback como dirección, lista enlazada de actores y selectores de sala/etapa.
La comprobación del enlace evita atribuir una entrada a otro actor o captura.
La ruta de impacto examinada consulta el banco opuesto al selector; por eso
se guardan ambos y el selector no se renombra universalmente como «banco leído».

**Conservados sin interpretar:** el resto de cada entrada de `0x120`, pool
de actores, posiciones inactivas y almacenamiento de eventos. La presencia
no define un tipo de esfera/cápsula/caja, radio, material ni canal de contacto.
Las direcciones y callbacks no se ejecutan ni se convierten en punteros host.

**Fuera del perfil:** contenido completo, longitud y terminación de las
listas geométricas, primitivas, winding/normales físicas, espacios/unidades,
transformación local/mundo de colisión, reglas de contactos y activadores.
El auditor histórico acotaba 80 bytes por puntero; eso no prueba que una lista
o forma mida 80 bytes. Esta tarea conserva únicamente sus huellas de inspección
en el inventario, sin publicar bytes originales ni prometer su decodificación.

### Candidatos de recursos

En el inventario F02.07 hay **285 indicios `.cld`**, ninguno vacío, con
**186 tamaños diferentes**, de **1.072 a 48.784 bytes**, total 2.690.720 bytes.
La selección exploratoria por tamaño conserva tres IDs/hashes (mínimo, mediana
por orden `size/id`, máximo) en el comprobante local. Son puntos de partida
para investigación del cargador/consumidor, no ejemplos positivos de formato.
La categoría `collision` del inventario sigue `unresolved` con razón
`no_validated_format_or_semantic_link`; no se reescribe ese inventario histórico.

Antes de un perfil de formas se debe demostrar la relación recurso → cargador
→ listas → consulta, sin deducirla de sufijos, tamaños o proximidad en memoria.
El uso del mismo nombre de sala tampoco demuestra que malla y colisión sean
equivalentes.

## Contrato preparado para implementación

La conservación se acota a ocho rangos por captura, **52.389 bytes** en total:
registros de personaje/escenario, almacenamiento/contador de eventos,
pool/cabeza de actores y etapa/sala. Para 30 capturas son **1.571.670 bytes**
de adjuntos previstos, sin guardar otra copia de 30 RAM completas.

El diseño separa decoder puro de registros, adaptador intermedio, preparador
de I/O y writer privado. El intermedio completo contendrá JSON, referencias y
240 adjuntos; producirá una vista de observación reproducible sin abrir los
estados originales. La salida prevista de 242 archivos más manifiesto todavía
no se ha creado. Se definen límites, errores, pruebas propias y comparación
privada antes de implementar.

La cola no vacía queda como variante no soportada en v1. Las semánticas de
daño/muerte siguen abiertas; retener los informes no equivale a observarlas.
El resultado conserva `capabilities=[]` y no habilita un solver jugable.

## Procedencia y reproducción

| Fuente | Bytes | SHA-256 |
|---|---:|---|
| ELF europeo `SLES_514.34` | 3.395.784 | `cb6e538bed7de8317f5333f3a56d4cd125432643950988168f901d6ede09f789` |
| Overlay `amusement_02` | 36.992 | `414142dad62fefc1cbd0d6684c05ba5d3331dd445949a11e5301470250683bde` |
| Informe SC-T3b.1 | 268.329 | `21b2f80f3158941cec2a17974e9136cbd2f810443726f9d87b7e09fc107e6d35` |
| Informe SC-T3b.2 | 14.472 | `1fb3f1828a5ffb392d04ca92ceb25b6461d3bef222233319e71d5130a26bd3a5` |
| Informe de continuidad | 21.464 | `ea78b9d400712f07616794b0382da196bf5a9bb57b55d53c9002109a9914163c` |
| Inventario de candidatos A/B, cada uno | 1.970.573 | `d5e6de2d1c03f053cedeb488390b5d250f5129aba804ab4fbac54eaeb81a3c57` |
| Inventario nuevo IR-T7a | 190.608 | `c7f7a95b1bb191d956a9524ea601ed0d0fc3c76ce303b44975aac4524a8e6c69` |

Las capturas se conservan bajo
`/Users/germancontreras/sh3-private-data/f03-02-skeleton-continuity-v5/`.
El inventario nuevo `reports/local/f03-04-collision-inventory-v1.json` contiene
hash/tamaño individual de los 30 estados y recibos, 240 rangos propuestos,
huellas acotadas de punteros, conteos por captura y hashes de auxiliares.
Solo contiene metadatos; no exporta RAM, instrucciones, geometría o texeles.
Auditor local `build/collision-intermediate/inventory.py`, SHA-256
`afe27cd9e4bee3d8b8156ff0bce67ca85a380069044db1b42d26743d21a11507`.

```sh
rtk proxy .venv/bin/python build/collision-intermediate/inventory.py
```

Sin `--output`, vuelve a verificar y muestra el hash sin escribir. Con
`--output reports/local/<nombre-nuevo>.json` crea exclusivamente un archivo
nuevo con modo 0600. Requiere la ISO privada, capturas, informes y auxiliares
locales; no es una herramienta del pipeline público ni depende de una VM activa.
Los puntos de entrada de los auditores antiguos no se invocan, porque
reescribirían sus informes. Se reutilizan sus lectores y comprobaciones.

El contrato se revisa por trazabilidad y consistencia. Se ejecutan controles
de repositorio, enlaces locales y whitespace; no se añade un test que solo
compruebe la presencia de palabras en Markdown. La batería sintética y el gate
de cobertura corresponden a IR-T7c–e, al implementar código de producción.
Resultado local: repositorio **PASS, 0 errores**; hashes del inventario y
auxiliares, enlaces, presupuestos de rangos y `git diff --check` aprobados.

## Siguiente tarea

**[IR-T7c completada](f03-04-collision-registry.md):** decoder puro con 100
tests sintéticos y cobertura 100 %. Reconstruye la lista de actores y ambos
registros sin alterar los bytes opacos y rechaza límites/enlaces inválidos.
Sigue IR-T7d: adaptación al intermedio y publicación privada; después comparación
de dos conversiones de las mismas fuentes. No se denominan extracciones
independientes ni se exige una nueva prueba en 2DS XL para este perfil.
