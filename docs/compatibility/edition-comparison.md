# Edición europea observada

Fecha: 2026-10-16. Entrada proporcionada por el usuario en `binaries`. La inspección se realizó en lectura y se repitió contra el perfil local completo. Los dos pases coinciden en la identidad de la imagen y los 113 archivos.

| Campo | Evidencia local | Límite de la conclusión |
|---|---|---|
| Región | Europa, confirmada por el usuario | No deducida del nombre del archivo |
| Serial | `SLES-51434`; ejecutable `SLES_514.34` | Derivado del `BOOT2` de `SYSTEM.CNF` |
| Modo de vídeo | `PAL` | No acredita tick, frame rate ni temporización del juego |
| Versión del contenido / VER | `1.02` | Arranque y catálogo contrastados mediante los checksums de la imagen completa |
| Ejecutable | ELF32, little-endian, MIPS, tipo ejecutable | Solo cabecera; no prueba portabilidad a ARM |
| Imagen | 3.586.785.280 bytes | ISO9660, sin montar ni extraer |
| Archivos | 113; 3.484.361.619 bytes de contenido lógico | Catálogo de archivos, no de entradas internas de MFA/AFS |
| Idiomas catalogados | Inglés, francés, alemán, español e italiano | Identificados por coincidencia con Redump 1064; ejecución y cobertura del port pendientes |
| Perfil | `ps2-sles-51434-9a94b95e777dae42` | Identidad contrastada con catálogo; capacidades vacías, sin extractor ni compatibilidad anunciada |

SHA-256 de la ISO:

```text
9a94b95e777dae426043e40df1b70d77c8f6960dbd79af10df1cd592cf99ad91
```

| Archivo | Bytes | SHA-256 |
|---|---:|---|
| SYSTEM.CNF | 56 | `6521aa213e146a5982142030e354fc1d612d775aa5da62fdc7a86271662337fa` |
| SLES_514.34 | 3.395.784 | `cb6e538bed7de8317f5333f3a56d4cd125432643950988168f901d6ede09f789` |
| B0.MFA | 509.952 | `aa1a9e1b934112c17050f5198ae900255721fec9cdd2727847e0c5459edf960d` |
| 0FLIST.DIR | 1.527 | `598035c3d14942d8184887531b98017b13e3e1c9058948503c8372fca3886c3f` |

El catálogo contiene 62 nombres `.MFA`, 35 `.AFS`, 11 `.IRX`, uno `.IMG`, uno `.BIN`, el ejecutable, la configuración y el índice `.DIR`. Es una agrupación por extensión; no acredita todavía formatos internos ni cobertura de decodificación.

## Comparación con el PDF

El candidato del PDF es `ps2-ntsc-u-1.02`. La copia aportada declara Europa y arranca en PAL, por lo que se registra por separado. La coincidencia textual de `1.02` no demuestra equivalencia. No hay un manifiesto de hashes del candidato estadounidense contrastado en esta ejecución; no se inventa una comparación binaria ni se reutilizan sus offsets, símbolos o direcciones.

F00.02 y F00.03 están completadas para la identificación y separación de perfiles. Q02 está resuelta por coincidencia con el catálogo; [evidencia de cierre](../execution/f00-02-edition-identification.md). F00.04/Q03 definió el [alcance M0-M5](../scope.md), con español y Normal/Normal en la primera alpha. [F00.05](../execution/f00-05-profile-custody.md) completó perfil y custodia; [F00.06](../execution/f00-06-provenance.md) completó la revisión inicial de procedencia. [F00.07](../execution/f00-07-decisions.md) completó el registro de riesgos y aprobó G00 para identificación, alcance y custodia. F02 conserva formatos, entradas internas, dependencias y corpus del slice como trabajo pendiente.

Para continuar: F01.01 ya completó la evidencia del ejemplo oficial reproducible; F01.02 completa la validación de la aplicación sintética. El registro Q01-Q14 conserva los pendientes de adopción [LIC01-LIC09](licenses.md). Con G00 aprobada, F02.01 podrá abordar el índice y un contenedor europeo al verificar las herramientas correspondientes y disponer de raíz privada externa para derivados. El tick continúa siendo una incógnita de comportamiento; no se asume temporización NTSC a partir del PDF.

Implementación, comandos y pruebas: [informe de inspección](../execution/europe-iso.md). Custodia: [política de datos](../private-data.md).
