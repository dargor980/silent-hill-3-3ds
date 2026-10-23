# F03.04 / IR-T7c — Decodificador de registros de colisión

2026-10-23. **IR-T7c completada** conforme al
[contrato IR20/IR21/IR24](../../schemas/collision-intermediate-v1.md).
Se implementa el decoder de registros; el adaptador intermedio, preparador,
publicación y comparación privada de IR-T7d–f permanecen pendientes.

## Resultado

`tools/pipeline/collision_registry.py` incorpora `decode_registry(ranges)`.
Recibe exactamente ocho buffers `bytes`, con las longitudes fijadas, y devuelve
una observación nueva de etapa/sala, actores, personajes, escenario y eventos.
`CollisionRegistryError` expone códigos estables sin incluir datos originales
en el mensaje. El layout de rangos se expone como mapping inmutable.

El recorrido de actores verifica límites y alineación del pool, enlaces
anteriores y ciclos; las direcciones únicas acotan el recorrido a 32 slots.
Cada entrada de personaje debe pertenecer a un actor activo de ese mismo
conjunto. Se conservan ambas entradas de un propietario repetido, el orden
de la lista y ambos bancos, incluidos sus selectores independientes.

El registro de escenario conserva punteros ordenados, duplicados y su límite
de lectura histórico. No transforma esos punteros en propietarios aunque
coincidan numéricamente con una dirección de actor. Las palabras de presencia,
funciones y callbacks se mantienen como enteros; no se ejecutan ni se les
asigna una semántica de forma física. La cola no vacía se rechaza como variante
no soportada, separada del error de contador fuera de capacidad.

La observación derivada no contiene todos los bytes de entrada: **los ocho
buffers originales se mantienen intactos y el adaptador IR-T7d deberá
conservarlos**. No se reescriben espacios inactivos, formas desconocidas o
almacenamiento residual de eventos, ni se interpretan como floats. Esta tarea
no implementa todavía la serialización ni afirma un round-trip del paquete.

## Diseño y límites

El módulo solo depende de la biblioteca estándar, sin I/O ni dependencia de
auxiliares locales de investigación. Las funciones separan validación de
rangos, lista de actores, registro de personajes y registro de escenario.
El preparador posterior será responsable de hashes, identidad PCSX2,
procedencia de fase y cotejo con informes; el decoder valida la estructura.

Por ello acepta conteos estructuralmente válidos desde cero hasta capacidad
y las salas `0xEA/0xEB`, sin inferir que sean el control 02 o una captura del
segmento 08–35. La identidad de una observación seguirá incluyendo el hash
de captura al componerla. No se comparan tipos/instancias como IDs globales.
F03.04, G02/G03, respuesta física, formas CLD y transiciones de daño/muerte
permanecen abiertas.

## Pruebas sintéticas

**100 casos aprobados; 100 % de líneas (88/88) y ramas (42/42)** en el módulo
nuevo. Gate independiente de líneas/ramas ≥80 % aprobado. Fixtures generados
con bytes propios y offsets explícitos del contrato, sin usar las constantes
de producción para construir sus tamaños o sus valores esperados.

| Familia | Comprobación |
|---|---|
| Valores y orden | Oráculo completo de dos actores en orden inverso de slots, bancos distintos, propietarios duplicados, palabras u16 máximas y callbacks u32. |
| Límites válidos | Listas vacías, uno y 32 actores; 32 entradas de personaje por banco, 16 punteros de escenario, ambos selectores y extremos de puntero. |
| Conservación | Entradas originales sin alteración; cambios en bytes opacos/residuales no cambian la vista; modificar la salida no altera entradas ni futuras decodificaciones. |
| Lista y pertenencia | Enlaces fuera de pool/desalineados, ciclos de uno o varios actores, enlaces anteriores incorrectos y propietarios no activos, incluso dentro del pool. |
| Registros y contexto | Conteos/selector inválidos en cualquiera de los bancos, punteros fuera de RAM, etapa/sala no soportadas y cola no vacía frente a contador inválido. |
| Entrada | Cada uno de los ocho rangos truncado, ampliado o mutable; tipos no admitidos y nombres faltantes/extra/ajenos. |
| Optimización Python | Dos subprocesses con `-O` rechazan un contador excesivo y una cola no vacía: la validación no depende de `assert`. |

```sh
rtk proxy .venv/bin/python -m pytest tests/python/test_collision_registry.py \
  --cov=tools.pipeline.collision_registry \
  --cov-report=json:build/collision-intermediate/decoder-coverage.json \
  --cov-report=term-missing \
  --junitxml=build/collision-intermediate/decoder-pytest.xml -q
rtk proxy .venv/bin/python -m tools.qa.coverage_gate \
  build/collision-intermediate/decoder-coverage.json
```

El job Python existente descubre estos tests y aplica el gate sin originales
ni cambios de YAML. Ruff y formato aprueban el alcance de CI de 243 archivos.
No se ejecuta CI remoto ni se recompila ARM: esta tarea no modifica el visor.
La comprobación de repositorio y los enlaces se verifican localmente.
El inventario privado IR-T7a queda intacto; no se releen estados ni se abre
PCSX2 para atribuir una validación real a las pruebas sintéticas.

Comprobante local `build/collision-intermediate/decoder-validation-v1.json`,
SHA-256 `7eba0bbcb703c078563429191cb0e5e5e0693fb810e5f269da26c1cef93f4ea3`.
Incluye hashes de módulo, tests, contrato, cobertura y JUnit. Repositorio:
**PASS, 0 errores**; enlaces, whitespace y hash del inventario anterior: PASS.

## Siguiente tarea

**IR-T7d: incorporar el decoder al adaptador y preparador intermedios.**
Verificar entradas fijadas y fases, conservar documentos/rangos completos,
reconstruir la vista al leer, publicar exclusivamente en la raíz privada y
probar errores de integración. IR-T7e/f cerrarán la batería del conjunto y la
comparación de dos conversiones de las mismas capturas. Esta entrega no
requiere otra prueba del visor en 2DS XL.

**Seguimiento IR-T7d:** [integración completada](f03-04-collision-intermediate.md).
El resultado anterior describe el cierre histórico del decoder; ahora existen
adaptador, preparador y writer, con cotejo en memoria de 30 capturas.
IR-T7e/f siguen pendientes.
