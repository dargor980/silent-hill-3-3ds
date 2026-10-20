# F02.07 — RDebug en el artefacto final (SRC89)

Fecha: 2026-10-18. Contrato [RD01–RD08](../../schemas/rdebug-artifact-v1.md).
Esta unidad continúa el candidato [SRC88](f02-07-pine-link.md), sin modificar
fuente, binarios, instalación ni perfil de admisión.

## Alcance observado

CMake declara siete fuentes RDebug y su lista de headers, pero las variables
aparecen una sola vez, en su declaración. El target no las incorpora. Se fijan
por hash los dieciséis archivos de ese directorio y la configuración empleada.

La auditoría contrasta esa lectura con:

- **825 entradas de compilación**, sin unidades RDebug.
- **403 objetos directos** y **19 archivos estáticos**, con 409 miembros,
  enumerados desde la instrucción efectiva de enlace; no hay archivos de respuesta.
- **806 archivos de dependencias del compilador**, incluidos todos los objetos
  directos del enlace, sin referencias al directorio RDebug.
- **42 Mach-O del candidato**, con hashes previamente verificados, inspeccionados
  mediante nm. Se buscan ocho símbolos específicos fijados desde las fuentes
  RDebug, evitando confundirlos con los servicios DECI2 del sistema invitado.

Las 61 invocaciones ar/nm terminan correctamente. El ejecutable conserva como
controles positivos PINEServer::Initialize(int) y PINEServer::Deinitialize().
No se encuentran los símbolos RDebug seleccionados. El resultado combina la
selección efectiva de fuentes y entradas de enlace con símbolos; no depende
solo de que nm deje de mostrar código eliminado por LTO/dead stripping.

## Controles y límites

Siete mutaciones de los datos de auditoría deben rechazar la conclusión:
fuente RDebug compilada, objeto RDebug enlazado, dependencia RDebug, símbolo
RDebug, salida de herramienta ausente, herramienta fallida y control positivo
ausente. Todas se detectan. Son controles del verificador; no se compila ni
arranca un servidor RDebug de prueba.

Las salidas completas, entradas de enlace y hashes de objetos/dependencias
quedan privadas. Se publican metadatos y recibos, sin cuerpos del proveedor ni
originales del juego. Dos reportes idénticos verifican las entradas y custodia.
El primer lanzador de auditoría falló porque un script local llamado inspect.py
ocultaba el módulo homónimo de Python. Se conserva y una nueva versión aísla
la ruta de imports; ese fallo no modificó fuentes ni la etapa privada.

RD-T1–3 acredita evidencia de ausencia del componente RDebug examinado en este
candidato macOS x86_64 fijado. No acredita otras plataformas, plugins externos,
modificaciones en memoria o cualquier ejecutable distinto. No se convierte en
un hecho de producción: rdebug_excluded sigue desconocido hasta vincular el
proceso que captura con el artefacto y verificar su ciclo de vida.

La continuación debe definir esa vinculación de identidad y las condiciones
restantes del perfil: VIF dinámico, escritores/backend y frontend/VM. El
resultado de transporte y este inventario no habilitan AD-3 por sí solos.
No se inició VM ni se capturó memoria del juego; admisión y capacidades vacías.
