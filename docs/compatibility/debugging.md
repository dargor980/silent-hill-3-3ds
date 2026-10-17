# Depuración del diagnóstico — F01.05

[Contrato EARS D01-D06](debugging-contract.md). Estado: build y verificación de símbolos completados; breakpoints alcanzados en Azahar; incidencia de refresco tras reconectar GDB abierta. **Consola no probada**. Evidencia exacta en el [informe F01.05](../execution/f01-05-debugging.md) y [registro de entorno](debugging-evidence.json).

## Identidad antes de depurar

Usar `build/f01-05/artifacts/`, build **db2dd53fb5dc**. Copiar el 3DSX y `probe.txt` a `/3ds/sh3_diagnostic/` de la SD física o emulada; conservar ELF, `build-id.txt` y `debug-bundle.json` en el ordenador. Verificar el par antes de iniciar la sesión:

```sh
rtk proxy .venv/bin/python -m tools.debug.bundle verify --directory build/f01-05/artifacts --build-id db2dd53fb5dc
```

Para archivos copiados a otra carpeta, usar `--directory <carpeta-copia> --manifest <manifiesto-conservado> --build-id <ID-registrado>`. El ID esperado procede del registro de esa sesión. No crear un manifiesto nuevo para hacer pasar una pareja mezclada. El verificador no ejecuta archivos, no analiza DWARF y no certifica qué binario está cargado en el dispositivo: contrastar el build en pantalla y hash transferido.

El pipeline genera el manifiesto después del enlace y lo conserva en CI junto al ELF/3DSX. Un segundo build sobre una carpeta que ya contiene un manifiesto registrado se rechaza antes de compilar. Para el siguiente ensayo conservar la carpeta anterior y usar una copia limpia; no sobreescribir evidencia para reutilizar su nombre.

## Azahar local

Se probó **Azahar 2126.2 ARM64**, [release oficial](https://github.com/azahar-emu/azahar/releases/tag/2126.2), ZIP SHA-256 `c24dec2bd5111b7d79513d686c5aece6612cdbf9737b2e6ea99cfc426f1d4aef`. Descargado/extractado bajo `build/f01-05/tools/`, sin instalación en Applications. No copiar datos de consola, firmware DSP ni originales al checkout.

En este paquete macOS, crear **`user/` al lado de `Azahar.app`** antes de abrirlo; dentro, `sdmc/3ds/sh3_diagnostic/probe.txt`. El frontend cambia su directorio de trabajo al contenedor del bundle. Las variables XDG no aislaron el primer ensayo: el log quedó en `~/Library/Application Support/Azahar/`; ese ensayo exploratorio se conserva por separado. Los ensayos posteriores sí usaron `user/` bajo build. [Entrada del frontend](https://github.com/azahar-emu/azahar/blob/2126.2/src/citra_qt/citra_qt.cpp), [selección del directorio](https://github.com/azahar-emu/azahar/blob/2126.2/src/common/file_util.cpp).

Lanzar el binario con `-g 24689 <ruta-absoluta-del-3dsx>` activa el servidor para el ensayo. El puerto es temporal y está registrado, no pertenece al protocolo del juego. Esta versión escucha en todas las interfaces; limitar la sesión a una red de confianza y cerrar Azahar al terminar. No dejar el servidor habilitado. [Implementación GDB de Azahar](https://github.com/azahar-emu/azahar/blob/2126.2/src/core/gdbstub/gdbstub.cpp).

Con el SDK fijado y las fuentes del build montadas en `/work`, los comandos de GDB usados fueron:

```gdb
set pagination off
set confirm off
set auto-load off
set remotetimeout 10
file /work/build/3ds/sh3_diagnostic.elf
break sh3::platform::ctr::run_diagnostic
target remote host.docker.internal:24689
continue
info registers pc
bt
list
```

`host.docker.internal` corresponde a Docker Desktop → Azahar host; desde un GDB nativo usar `127.0.0.1:24689`. No usar `load`: el emulador ya carga el 3DSX. GDB del SDK es 14.1. Con fuentes en otra ruta, usar `set substitute-path /work <raíz-del-snapshot>` antes de listar código. Comprobar el mapa de carga; si el binario no está en las direcciones del ELF, resolver el desplazamiento antes de usar breakpoints o simbolizar PC.

Para el error de audio observado: conectar y romper en `sh3::platform::ctr::Tone::snapshot`, continuar y consultar `this->status_`, `this->result_`, `this->initialized_`, `this->samples_`, PC y pila. Se observó init fallida, `0xd880a7fa`, servicio no adquirido y puntero nulo. No se proveyó DSP; no se acredita audio. No modificar registros o memoria para fingir un resultado correcto.

Los getters inline pueden no existir como funciones separadas en Release. `FileProbe::fixture_status` no resolvió como símbolo; `Tone::snapshot` sí. El punto de entrada `run_diagnostic` resolvió en la línea 18 por el constructor gráfico inline. Registrar la línea realmente devuelta, sin inventar una posición a partir del nombre. Las rutas de fuentes del SDK no están incluidas en el snapshot; el aviso de `svc.s` ausente no invalida la resolución de fuentes propios.

## Consola: procedimiento pendiente

No se presupone Luma3DS por disponer de Homebrew Launcher/FBI. Confirmar primero versión de firmware, launcher y Luma/Rosalina disponible. No se instala ni modifica firmware para esta tarea.

1. Verificar el manifiesto y copiar 3DSX/fixture. Registrar hash transferido, build visible, modelo New Nintendo 2DS XL, fecha y operador.
2. Si Rosalina está disponible, abrir su menú y habilitar temporalmente el depurador. Anotar IP y puerto mostrados. Para detener al iniciar usar la opción correspondiente a la siguiente aplicación; abrir el diagnóstico desde Homebrew Launcher.
3. Cargar el ELF verificado. Para break-on-start, el README actual de Luma documenta puerto **4003** con `target remote <IP>:<puerto>`. Para un proceso ya activo documenta puertos **4000–4002**, `target extended-remote`, `info os processes` y `attach <PID>`; seleccionar exclusivamente el proceso del diagnóstico. Confirmar contra la versión instalada, sin escanear la red ni adivinar IP/PID.
4. Comprobar direcciones de carga, alcanzar el breakpoint, registrar PC/pila/función/línea y continuar. Para un fallo controlado de archivo, cerrar el diagnóstico, renombrar solo su fixture y reabrir; registrar MISSING y la ruta de código correspondiente. Restaurar el fixture al terminar. No inducir fallos de memoria ni alterar datos ajenos.
5. Desconectar GDB, salir con START y deshabilitar el depurador en Rosalina. Registrar el retorno, reapertura y cualquier incidencia. Un breakpoint configurado pero no alcanzado queda no probado.

Fuente primaria: [README de Luma3DS](https://github.com/LumaTeam/Luma3DS#basic-usage), que advierte que su wiki está desactualizada. El procedimiento requiere contrastar la versión real. La ejecución física no queda cubierta por la conexión a Azahar.

## Registro por entorno

Guardar versión/arquitectura del emulador o modelo/firmware/launcher, CPU/configuración gráfica, ID y hashes del manifiesto/3DSX/ELF, PC y base de carga, breakpoint alcanzado, error observado y transcripción. Para esta tarea el perfil es sintético, sin revisión/idioma jugables. Conservar resultados fallidos: el refresco parcial observado tras reconexión GDB sigue pendiente de diagnóstico y no permite declarar estabilidad del emulador.
