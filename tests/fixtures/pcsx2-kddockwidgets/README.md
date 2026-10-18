# Consumidor KDDockWidgets 2.4.1

Código propio para [KDW](../../../schemas/pcsx2-kddockwidgets-v1.md).
No incluye fuentes, datos ni binarios del proveedor. Requiere el paquete exacto
KDDockWidgets 2.4.1 y Qt 6.11.1, frontend Qt Widgets.

## Contratos comprobados

| Caso CTest | Observación |
| --- | --- |
| `kdw_docking` | Contenido sintético, grupos separados, ventana común, flotar y reacoplar. |
| `kdw_tabs` | Agrupación de pestañas y cambio de pestaña activa. |
| `kdw_lifecycle` | Cierre/reapertura conservando el widget huésped y acoplamiento. |
| `kdw_memory` | Serializar, modificar y restaurar disposición desde bytes. |
| `kdw_file` | Guardar, modificar y restaurar desde archivo temporal. |
| `kdw_invalid` | Rechazar JSON malformado y objeto incompleto; recuperar con datos válidos. |
| `kdw_missing` | Rechazar archivo ausente; recuperar desde archivo válido. |
| `provider_includes` | Compilar y ejecutar `includes_test` original, incluidas sus cabeceras Qt Widgets. No es una prueba gráfica funcional. |

Las restauraciones comprueban IDs, estados abierto/acoplado/flotante, relación
de pestañas, pestaña activa, ventana asociada y conservación del contenido.
Se verifica que los tres paneles figuren en `restoredDockWidgets()` y que
`restoreInProgress()` termine. Cada caso corre en otro proceso; los archivos
de prueba se crean en un temporal que Qt limpia al salir.

`Scenario` encapsula creación y propiedad de widgets. Las aserciones y la
verificación de persistencia están separadas; la biblioteca se inyecta por
sus raíces CMake y el target `KDAB::kddockwidgets`. No hay dependencias del
runtime del juego ni red durante las pruebas.

## Configuración

Pasar a CMake `SH3_KDD_CMAKE_ROOT` (directorio que contiene el config del
paquete), `SH3_QT_CMAKE_ROOT` (`lib/cmake` de Qt) y, para el test original,
`SH3_PROVIDER_SOURCE` (fuentes originales privadas). Las dos raíces de paquetes
son obligatorias y se rechazan si faltan, sin recurrir a paquetes globales.
Las opciones de arquitectura/toolchain deben coincidir con las dependencias.
Construir y ejecutar CTest con `--output-on-failure` y `--output-junit`.

El proveedor exporta por defecto solo el paquete de instalación. Para probar
antes de instalar, configurar su build con
`CMAKE_PROJECT_KDDockWidgets_INCLUDE` apuntando a `export-build-tree.cmake`:
el hook exporta el target existente al terminar la configuración y no cambia
las fuentes ni las opciones funcionales de la biblioteca. Usar su directorio
`src` como `SH3_KDD_CMAKE_ROOT`. Después de instalar, configurar otro consumidor
con `lib/cmake/KDDockWidgets-qt6` del prefijo final.

## Límites

`QT_QPA_PLATFORM=offscreen` valida estados mediante API y eventos, sin arrastre
real, apariencia, foco nativo ni posiciones exactas dependientes de pantalla.
No ejecuta la suite gráfica completa del proveedor: esa suite requiere su
perfil `DEVELOPER_MODE` y APIs de testing adicionales. Qt Quick, Python,
Wayland, ejemplos y documentación quedan excluidos del build de esta unidad.
El test original de includes permanece sin cambios en la carpeta privada.
Su primera compilación contra el paquete instalado detectó la omisión de
`qtwidgets/Platform.h`. La copia de trabajo final agrega una única regla
CMake para instalar esa cabecera original; los consumidores y sus
expectativas no se modificaron para superar el fallo.
Los logs, trazas de carga, supervisión de capacidad y JUnit locales están
inventariados por hash en la evidencia; esto no implica ejecución en CI remota.
