# F02.03 — variante B8 y nombres de XBG0

Fecha: **2026-10-17**, America/Santiago. **Investigación completada:** B8 implementado y contrastado; XBG0 cerrado como investigación con codificación pendiente y rechazo explícito. [Ticket](../specs/sh3-3ds/tasks/F02.md#f0203), [contrato EARS MV01-MV08](../../schemas/mfa-probe-v2.md). El resultado no cierra G02 ni demuestra extracción o contenido jugable.

## Resultado

| Selección fija | Candidatos por extensión | Archivos estructuralmente aceptados | Bloques aceptados | Entradas aceptadas | Desconocidos bajo esa selección |
|---|---:|---:|---:|---:|---|
| B8 | 62 | 59 | 64 | 1693 | B0, MV0 y XBG0: `MFA_TABLE` |
| D8 | 62 | 2 | 2 | 47 | 59 B8: `MFA_TABLE`; XBG0: `MFA_NAME` |
| Unión de los dos conjuntos disjuntos | 62 | **61** | **66** | **1740** | **XBG0** |

Cada selección se ejecutó dos veces y produjo JSON idéntico dentro de su par. La unión se calculó por ruta y se comprobó que ningún archivo estaba aceptado por ambas políticas. No se suman bloques parciales de XBG0. Estos conteos describen estructura de MFA, no cobertura de campaña, formatos de payload, AFS u otros archivos del disco.

Una observación inicial de las dos cabeceras conocidas encontró 59 con cabecera B8 plausible y 3 con D8 plausible, sin ambigüedad. La plausibilidad solo comprueba cantidad/tabla y extensión del área de datos: no acepta el archivo. La validación posterior recorrió todos los bloques/nombres/rangos de cada candidato aceptado. No se busca un offset que produzca éxito ni se cambia de selección ante fallo.

Se reutiliza la procedencia fijada en [F02.02](f02-02-mfa-candidate.md). No se consultó otra versión del candidato ni se ejecutó/adoptó su código. El único cambio de layout B8 respecto a D8 es la tabla inicial en 0xB8; las continuaciones usan base + 8. La palabra de significado desconocido conserva ese estado; no se atribuye semántica por coincidir su valor.

## Investigación de XBG0

El diagnóstico vuelve a localizar el rechazo en la **entrada ordinal 237**, bloque índice 4 (índices de bloque/entrada desde cero), entrada del bloque índice 43. Base del bloque: **65.947.648 bytes**; nombre en offset relativo **936**, longitud **33 bytes**, de los cuales **8 son no ASCII** y **0 controles**.

| Candidato de codificación | Decodificación estricta | Recuperación exacta de bytes al recodificar |
|---|---|---|
| UTF-8 | No | No |
| Shift-JIS | Sí | Sí |
| CP932 | Sí | Sí |

La coincidencia de dos candidatos no identifica la codificación original. No hay evidencia suficiente para adoptar uno ni para afirmar corrupción. La política continúa exigiendo ASCII imprimible; XBG0 queda `unknown`, `encoding=unresolved`. No se sustituyen caracteres, se ignoran errores ni se usa Latin-1 como salida automática. No se publicaron ni guardaron cadenas crudas, hexadecimal o base64 del nombre.

La investigación cumple la opción de informe de limitación del ticket. Su extracción sigue pendiente. F02.04 debe separar identidad por origen/posición/hash de la futura ruta del host; no convertir automáticamente el nombre desconocido en un nombre de archivo. Aceptar nombres opacos requerirá un contrato y pruebas propios, con un estado de soporte explícito.

## Identidad y evidencia

Cada sondeo verifica primero la imagen completa y los tamaños/hashes de los 113 archivos del perfil. Imagen europea SLES-51434/PAL 1.02: **3.586.785.280 bytes**, SHA-256 `9a94b95e777dae426043e40df1b70d77c8f6960dbd79af10df1cd592cf99ad91`. Perfil canónico: `ps2-sles-51434-9a94b95e777dae42`, 17.037 bytes, SHA-256 `504cb4aa3a0a24480324d2853a153ff9c77ac7b8987b3665566b8ed8f9a620d9`. Sin modificación del perfil ni de la ISO; estabilidad comprobada al cerrar.

Metadatos privados, confirmados como ignorados por Git:

| Par de informes en `reports/local` | Tamaño de cada informe | SHA-256 compartido |
|---|---:|---|
| `f02-03-b8.json`, `f02-03-b8-repeat.json` | 48.258 bytes | `ab18679b04c367d3bec590f580ce19814b25c9c4c9dec6e454bd4a3f0d2d387f` |
| `f02-03-d8.json`, `f02-03-d8-repeat.json` | 23.629 bytes | `bcb01df5a1874fdecb874b536cca1bb12a079f7d9a8c01609d7599e300c8ae6d` |

`f02-03-header-observations.json`: 31.894 bytes, SHA-256 `c940199a95cbb3f20c8fb1eaa9c9d0d21bcd30d0694f002cb86609a0e0389ac2`; solo observaciones numéricas de cabeceras. Los informes v1 de F02.02 permanecen sin sobrescribir. Los nuevos informes son esquema/herramienta v2, con selección y contexto de error; los layouts mantienen su identificador de política v1.

No se exportan recursos. El hash de identidad lee todos los bytes; el parser solo lee sectores de metadatos de 2048 bytes. No se calculan todavía hashes por recurso ni se descodifican payloads. No hace falta raíz externa para esta inspección; sigue siendo obligatoria para la extracción futura.

## Implementación, SOLID y validación

`mfa.inspect_layout` comparte validación entre B8/D8; `inspect_d8` conserva su interfaz. El selector solo admite claves registradas y rechaza ambigüedad de cabeceras. `mfa_names.name_diagnostics` es una función pura, acotada a 1024 bytes, que describe candidaturas de codificación sin decidir aceptación. `MfaError` añade contexto seguro de la entrada; `ProfileError` de lectura continúa abortando toda la operación. `mfa_probe` compone selección/verificación/JSON sin duplicar el lector ISO ni añadir dependencias.

**493/493 pruebas Python aprobadas**, incluidas **63 nuevas**; las 136 focalizadas MFA/D8/B8 también pasaron. Se preservaron las aserciones de las 73 pruebas MFA anteriores. Casos adicionales: cadenas de múltiples bloques, variante equivocada sin fallback, layout no registrado, ambas cabeceras plausibles, rangos/rutas/colisiones/solapamientos/budgets compartidos, continuación con tabla incorrecta, lecturas cortas, nombre inválido en bloque posterior, codec que decodifica pero no recupera los mismos bytes, estadísticas sin cadenas originales, contrato memoria/ISO, CLI repetible, identidad y fallos de transporte.

Cobertura Python: **1012/1042 líneas (97,12 %)** y **385/402 ramas (95,77 %)**. `mfa.py` y `mfa_names.py`: **100 % de líneas y ramas**. Gate independiente ≥80 %, Ruff check/format y contratos de arquitectura/custodia/specs verificados en `build/f02-03/quality.log` y `verification.json`. Ruff detectó un argumento UTF-8 redundante en un fixture; se corrigió sin cambiar sus bytes y se repitió su caso.

Entorno local: Python 3.14.6, pytest 9.1.1, pycdlib 1.22.0, Ruff 0.17.1. Se conserva en `build/f02-03` el log completo, JUnit, cobertura JSON/XML, comandos y manifiesto de fuentes. La CI quality existente descubre estas pruebas y aplica los gates con datos propios. No necesita ISO ni red; no se ejecutó GitHub Actions remotamente. Runtime C++/ARM sin cambios, por lo que sus builds y pruebas físicas no se repitieron; G01 sigue pendiente.

## Reproducción y siguiente tarea

Desde la raíz, con salida nueva; repetir con `--layout d8` para la otra hipótesis:

```sh
rtk proxy .venv/bin/python -m tools.inspectors.mfa_probe \
  --iso 'binaries/Silent Hill 3 (Europe) (En,Fr,De,Es,It).iso' \
  --profile reports/local/europe-profile-identified.json \
  --image-sha256 9a94b95e777dae426043e40df1b70d77c8f6960dbd79af10df1cd592cf99ad91 \
  --layout b8 \
  --output reports/local/f02-03-b8.json
```

Las repeticiones usan destinos `-repeat.json`; no sobrescribir los existentes. `build/f02-03/probe-commands.json` conserva cada comando y resultado.

**F02.03/B8 completada con estructura verificada. F02.03/XBG0-nombres completada como investigación con soporte pendiente.** El siguiente ticket es **F02.04: catálogo interno con IDs, offsets, hashes y dependencias conocidas**, conservando desconocidos. XBG0, AFS y otros formatos requieren instancias explícitas antes de anunciar cobertura de extracción/corpus. Q05/G02 y la consola G01 siguen abiertos.

## Identidad de fuentes

`build/f02-03/source-manifest.json`: 55 archivos, SHA-256 `5e82938eb895b6db519cdba3f15df826685bee29af6791d1af7f2179c1bd107a`. Registra fuentes propias, pruebas, contratos y configuración; excluye este informe para evitar autorreferencia y no incluye datos privados ni fuentes externas crudas. Los cambios permanecen sin commit.
