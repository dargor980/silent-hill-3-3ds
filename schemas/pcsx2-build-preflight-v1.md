# IB v1 — preparación del build instrumentado host

Extensión de [MP](effective-mapping-v1.md) para
`F02.07/origin/effective-mapping/instrumented-build`. Esta etapa prepara el build
base; no modifica PCSX2 ni adquiere mapas del juego.

## Requisitos EARS

- **IB01 — Origen.** CUANDO se prepare el checkout, el investigador DEBERÁ fijar
  PCSX2 al commit `fd9d310ccbb6b8b62c976da8886a3c8fd3a10ff3`, comprobar árbol
  limpio y conservar licencia, fuentes y manifiesto fuera del repositorio del
  port. SI hay una descarga incompleta, DEBERÁ conservar su estado sin anunciar
  éxito ni sustituir la instalación habitual.
- **IB02 — Capacidad.** ANTES de iniciar dependencias grandes o build completo,
  el procedimiento DEBERÁ comprobar espacio en su destino y disponer de una
  reserva de trabajo de 20 GiB. SI falta, DEBERÁ conservar estado pendiente y
  permitir únicamente diagnósticos pequeños. Esta reserva es política del
  proyecto, no tamaño medido ni requisito publicado por PCSX2.
- **IB03 — Toolchain real.** CUANDO evalúe preparación, el procedimiento DEBERÁ
  compilar y ejecutar un fixture propio x86_64 de C++20 y comprobar generación
  de AIR/metallib con Metal. Una versión de compilador o presencia de headers
  no sustituirá esos ensayos. SI falla una etapa, DEBERÁ omitir las dependientes.
- **IB04 — Configuración base.** CUANDO configure PCSX2, el procedimiento DEBERÁ
  usar directorio de build nuevo y prefijo de dependencias explícito, arquitectura
  x86_64 y fuentes sin parches. DEBERÁ conservar códigos/logs y distinguir
  compilador funcional, configuración de dependencias y build completo.
- **IB05 — Gate.** CUANDO evalúe resultados suministrados, el gate DEBERÁ exigir
  identidad de fuente, espacio suficiente y éxito de todas las comprobaciones.
  SI falta un resultado, un código no es entero o una prueba no se ejecutó,
  DEBERÁ rechazar la preparación. Un informe de preflight no acreditará build,
  tests del emulador, compatibilidad de estados ni adquisición real.
- **IB06 — Alcance.** MIENTRAS prepare el observador, el procedimiento DEBERÁ
  mantener fixtures, código host y datos de juego separados; no incluirá BIOS,
  ISO o capturas en CI ni instalará dependencias o cambiará ajustes globales
  desde el preflight. La instrumentación se realizará después del build base.

## Diseño y tareas

El gate es una función pura de resultados, sin ejecutar comandos. La captura de
resultados corresponde al procedimiento local; logs y rutas quedan privados.
Los fixtures C++20/Metal contienen datos propios y se versionan para repetir
la comprobación. El gate se integra en `quality` mediante pruebas Python.

La secuencia es: checkout verificado → fixtures de toolchain → configuración
base → evaluación. Solo después de un gate satisfactorio se inicia build
completo, tests y compatibilidad del estado. El espacio puede cambiar después
del preflight: se vuelve a comprobar inmediatamente antes del build grande.

El estado `ready_for_baseline_build` significa únicamente prerrequisitos
suministrados coherentes. No autentica los logs ni autoriza por sí mismo
acciones externas. Las pruebas reales locales quedan documentadas por hashes.

La observación externa MP02 ya falló con EPERM. La futura instrumentación
interna leerá su propio mapa durante pausa; no necesita obtener puertos Mach
ajenos ni cambiar las protecciones del sistema. Su protocolo aún debe
especificarse e integrarse tras la aceptación del build base.
