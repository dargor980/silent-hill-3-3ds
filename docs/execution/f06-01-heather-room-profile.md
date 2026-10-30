# HM-T4a — Selección y contrato de la primera habitación

2026-10-29. **HM-T4a completada.** Se selecciona **`hp34`** para la primera
escena nativa de inspección con Heather original. Quedan fijados recursos,
entrada, coordenadas, colisión admitida, cámara inicial y presupuesto en
[HR01–HR12](../../schemas/heather-room-profile-v1.md) y su
[perfil JSON](../../schemas/heather-room-profile-v1.json).
La escena aún no está integrada ni tiene un nuevo build físico.

## Elección basada en las fuentes

Se releyeron las extracciones A/B de cuatro pares MAP/CLD, verificando cada
ID, tamaño y SHA-256 contra catálogo y recibo fijados. El inventario MAP se
recorrió con los lectores existentes; se decodificó cada forma en memoria
para contar triángulos y verificar reconstrucción de sus registros. No se
exportaron vértices ni texturas al repositorio.

| Candidato | Formas / vértices / triángulos MAP | Colisión y transformaciones | Decisión |
| --- | --- | --- | --- |
| **hp34** | **31 / 15.882 / 9.300** | 34 polígonos; perfil de matriz base admitido; vidrio ya contrastado. | Seleccionado. |
| tp1d | 107 / 40.058 / 20.168 | 130 polígonos; `MR_TRANSFORM_CHAIN_UNSUPPORTED`. | Requiere ampliar transformaciones. |
| tp1e | 69 / 42.903 / 19.451 | 220 polígonos; `MR_TRANSFORM_CHAIN_UNSUPPORTED`. | Más geometría y transformación pendiente. |
| tpf1 | 185 / 45.183 / 22.451 | `CP_NONPOLYGON_UNSUPPORTED`, por grupo 4 activo. | No reabrir ahora la variante ni la investigación pospuesta. |

Los tres CLD aceptados coinciden en su vista completa tipada con el oráculo
independiente, incluido el signo del cero. Ambos lectores rechazan `tpf1`
con el mismo código. Sus polígonos no se publican como una aceptación parcial.
Los conteos de MAP son estructurales, no evidencia de consumo de todas las
formas en PS2. `tpf1` contiene diez triángulos degenerados; los otros tres,
cero. No se alteraron sus recursos para obtener estos resultados.

Fuentes seleccionadas, conservadas en privado:

| Recurso | Bytes | SHA-256 |
| --- | ---: | --- |
| hp34.map | 2.134.960 | `fe6661eeb4d7df7e3baf6cd015452e1c9d3548416a862e503e1f2370a1f289c9` |
| hp34.cld | 3.920 | `e49f5c97048fe95dd9109413bc37c854078fd0defeead3d4dbdbf8acdbfbaff0` |
| hp34TR.tex | 69.808 | `65173379ae86c13512b0c546edf68ae3a82b79b7267f5b011a39d8d44ccf35e4` |

La coincidencia de origen MAP/CLD se verifica numéricamente y se elige el
par para esta composición. **No se capturó el registro de `hp34.cld` en
PCSX2**, por lo que su vínculo en una fase del juego permanece sin acreditar.
La evidencia previa de matriz, textura y transparencia corresponde a las
dos formas 448/928 y a una cámara de diagnóstico, como indica
[MR-T4d](f03-02-map-draw-state.md).

## Entrada y alcance de contactos

Punto inicial de inspección: **mundo `(100275,0,140000)`, yaw 0, espera**;
local a la habitación `(275,0,0)`. Origen común `(100000,0,140000)`, base
`(X,−Y,−Z)` y escala de render 0,002. La posición de Heather, su pose local
y el MAP no se normalizan por separado. Se conserva el W de la deformación;
el visor aislado usa otra rotación y necesita el adaptador de escena nuevo.

El CLD tiene grupos **1/4/26/3/0**, todos referenciados una vez en celda 0.
El perfil nativo clasifica un suelo horizontal, un techo conservado sin
movimiento vertical y **32 bloqueadores**. Para cada bloqueador se proyecta
su caja envolvente X/Z, sin interpretar filtros de gameplay. Huella cuadrada
de semiextensión 175 más guarda de 1: extensión efectiva 176. Es una regla
conservadora elegida para inspección, no el solver ni el radio original PS2.

Se comprobó con fracciones exactas el segmento completo de los cinco tramos:
spawn→inicio y cuatro lados del recorrido local
`(230,−150) → (320,−150) → (320,400) → (230,400) → (230,−150)`.
Todos quedan dentro del suelo contraído y fuera de las 32 cajas expandidas.
La certificación incluye el interior ocupado de las cajas y las tangencias;
no se basa en puntos muestreados a lo largo de la ruta.

| Comprobación geométrica | Resultado |
| --- | --- |
| Spawn con extensión efectiva 176 | Libre. |
| Spawn, primera extensión que toca | 275; margen de 99 respecto a 176. |
| Recorrido, primera extensión que toca | 230; margen de 54 respecto a 176. |
| Extensiones de control 274 / 229 | Spawn / recorrido aún libres, respectivamente. |
| Centro sobre la barrera X local=0 | Rechazado. |
| Cruce de barrera con destino libre | Rechazado por el barrido. |

Los umbrales se contrastan con los límites analíticos de las dos barreras
paralelas más cercanas. Esta comprobación **no mueve a Heather ni acredita
que se haya recorrido la habitación**. El spawn es propio, no la entrada de
una puerta original. El encuadre y la relación visual entre malla y barreras
se verificarán durante HM-T4c.

La respuesta prevista al contacto es conservar toda la posición anterior,
sin avance parcial ni deslizamiento; giro y animación siguen el perfil HMN.
Escalones, rampas, gravedad, actores dinámicos y salidas a otras salas quedan
fuera. No se amplía el decoder CP ni se descartan silenciosamente registros.

## Materiales, memoria y dependencias

Se reverificaron manifiestos y los catorce payloads de cada paquete HL A/B:
SRI2 `2bc96e9f7fec9e52b21186d033ee02694b67808098bf101d304fd944c928fc0b`,
MDL522/ANM525, atuendo original y clips 101/109/113. Se conserva la validación
física anterior del visor HL; no se atribuye al nuevo escenario.

La primera composición mantiene Heather texturada, los dos paneles de
vidrio comprobados y **material neutro de diagnóstico para las otras 29
formas**, con indicación visible. Se conservará toda la geometría y no se
aplicará la textura del vidrio a las demás superficies. La asignación de
las siete texturas internas, sus paletas y estados sigue pendiente.

La fase diagnóstica prevé **17,5 MiB de texturas** combinadas. Expandir todas
las paletas declaradas del mapa requeriría 41 MiB, o **58,25 MiB con Heather**;
no es un inventario de variantes activas ni una estrategia admitida de carga.
El límite de texturas residentes queda en 32 MiB y el de memoria runtime
contabilizada en 64 MiB, ambos límites de proyecto sujetos a validación.
El VBO estático expandido se estima en **1.004.400 bytes**, bajo su reserva
de 2 MiB. La velocidad objetivo de 30 presentaciones/s deberá medirse.

Cámara fija de inspección definida en el perfil; el encuadre no se da por
aceptado antes de integrar. Los controles de HM-T3d se reservan al actor:
cruceta, B para carrera, A/R/L para reproducción y START para salir.

## Verificación y custodia

- **340 pruebas de regresión aprobadas**: MAP, geometría, metadatos de render,
  textura, decoder CLD y políticas de repositorio. JUnit local en
  `build/heather-room/pytest.xml`.
- Ocho controles geométricos elementales del auditor: intersección, tangencia,
  segmento nulo, exterior y pared de anchura cero; cuatro controles negativos
  del perfil contrastan umbrales, penetración y cruce.
- **60 fuentes fijadas y releídas al finalizar**, incluidas selección,
  catálogo/recibo, recursos A/B, paquetes HL, informes históricos y lectores.
- Auditoría normal y `python -O` producen **exactamente el mismo informe**.
- Políticas de arquitectura/custodia/EARS del repositorio: **PASS, 0 errores**;
  enlaces locales, perfil JSON y `git diff --check` verificados.
- No cambia código de producción ni CI; los gates nuevos pertenecen a la
  implementación HM-T4b/c. No se compila ARM ni se ejecuta CI remoto aquí.

Comprobante final: `reports/local/heather-room-profile-v2.json`, 16.868 bytes,
SHA-256 `1bd1c46e86f29075704b05f1e47edfe8fbfed21531572199d76737dc6c3a6630`.
La primera versión se conserva; la segunda añade pins de los lectores y
comprobación explícita de los conteos seleccionados, sin cambiar resultados.
Solo contienen metadatos; los buffers privados se procesan en memoria.

Perfil JSON: SHA-256
`5838c4b445a0da3f4a2636ac9c9e61edfe754dc89b33d25db33284581212e531`.
Auditor local `build/heather-room/audit_profile.py`: SHA-256
`d9c2a423c04a908c3d4472c277e2cedd1d2163cf20d0b65321d1f1590911782b`.
Sin argumento solo relee y muestra un resumen/hash; un argumento de salida
crea un informe nuevo exclusivo con permisos 0600. No modifica fuentes.

```sh
rtk proxy .venv/bin/python build/heather-room/audit_profile.py
rtk proxy .venv/bin/python -O build/heather-room/audit_profile.py
rtk proxy .venv/bin/python -m pytest -q tests/python/test_map_probe.py tests/python/test_map_geometry.py tests/python/test_map_render_probe.py tests/python/test_texture_probe.py tests/python/test_cld_polygons.py tests/python/test_repository.py
rtk proxy .venv/bin/python -m tools.qa.check_repository
rtk proxy git diff --check
```

## Siguiente tarea

**Actualización:** [HM-T4b.1 completada](f06-01-heather-room-contacts-contract.md),
con contrato numérico y vectores sintéticos del contacto plano conservador.
[HM-T4b.2 completada](f06-01-heather-room-contacts.md): núcleo y adaptador,
oráculo, atomicidad, cobertura, memoria y ARM.
[HM-T4b.3 completada](f06-01-heather-room-preparation.md): preparación privada
A/B y cotejo de las 32 cajas, suelo y recorrido.
[HM-T4c.1](f06-01-heather-room-scene.md) cerró datos/materiales/encuadre;
[HM-T4c.2](f06-01-heather-room-runtime.md), bucle compartido y ciclo de vida.
[HM-T4d](f06-01-heather-room-delivery.md) cerró el paquete de entrega.
La instalación SD está verificada; sigue la aceptación física HM-T5.
Se preservan C148 y la investigación HM-T2 pospuesta; no se reanuda PCSX2.
