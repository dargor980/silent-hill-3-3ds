# Identidad y perfil de diagnóstico — IP01–IP09

Como investigador quiero descartar un diagnóstico si deja de corresponder al
proceso observado. El resultado es evidencia de diagnóstico; no autoriza captura.

## Requisitos EARS

- **IP01:** WHEN se identifica una ejecución THEN SHALL distinguir artefacto,
  proceso, sesión de captura, época de VM y generaciones de PINE/VU/GS. Un PID,
  ruta, etiqueta Git o identificador recibido del cliente SHALL NOT sustituirlos.
- **IP02:** WHEN se vincula un artefacto THEN SHALL exigir el manifiesto aprobado
  del ejecutable y dependencias, y evidencia del proceso obtenida por un adaptador
  del proveedor. SHALL NOT aceptar un hash enviado por el cliente como atestación.
- **IP03:** WHEN el adaptador no puede acreditar el proceso, su inventario cargado
  o una lectura estable THEN SHALL entregar ausencia de observación. El consumidor
  SHALL descartar el diagnóstico, incluso si la lectura posterior vuelve a coincidir.
- **IP04:** WHEN cambia PID, nacimiento del proceso, nonce del proveedor, identidad
  de archivos, imágenes cargadas, revisión del cargador, época host o generación
  de PINE/VU/GS THEN SHALL descartar permanentemente la evaluación en curso.
- **IP05:** WHEN se sustituye un archivo por otros bytes o por otro objeto del
  sistema de archivos con los mismos bytes THEN SHALL invalidar la vinculación.
  WHEN se reinicia el proceso THEN SHALL exigir otra evaluación, aunque PID y
  contadores vuelvan a tener los mismos valores.
- **IP06:** WHEN se emite un perfil THEN SHALL conservar los dieciocho hechos de
  AP como satisfecho, violado o desconocido, sin convertir evidencia estática en
  estado runtime ni asumir exclusión por observar una VM pausada.
- **IP07:** WHILE VIF dinámico o escritores/frontend/VM no estén cubiertos THEN
  SHALL mantener admisión y capacidades vacías. Un diagnóstico compatible con el
  artefacto SHALL NOT modificar el sampler, armar LifetimeGuard o llamar read_ram.
- **IP08:** WHEN falla o termina una evaluación THEN SHALL conservar la primera
  causa, borrar el perfil pendiente y prohibir reutilizar la instancia. Los
  resultados históricos SHALL NOT presentarse como autorización vigente.
- **IP09:** WHEN se verifica este contrato THEN SHALL probar pérdida de identidad,
  PID reutilizado, cambios de archivos/dependencias/generaciones, retorno al valor
  anterior, hechos desconocidos y terminales; SHALL distinguir dobles de pruebas
  contra el proceso real.

## Diseño y límite de confianza

`tools.inspectors.process_diagnostic` contiene un consumidor independiente con
un puerto `IdentityProbe.sample()`. El adaptador obtiene la identidad; el
consumidor compara e invalida; el publicador custodia el informe. No hay parser
JSON, socket, acceso a RAM ni modificación de PCSX2 en este módulo. Los tests
inyectan un doble del puerto. Python Protocol y las dataclasses no autentican
un emisor: **todavía no existe un adaptador productivo para este puerto**.

El manifiesto esperado, fijado por quien lanza el candidato, contiene hashes del
ejecutable y bibliotecas empaquetadas, identificados por nombres relativos. El
adaptador debe comprobar el conjunto completo en disco y las imágenes realmente
cargadas. La evidencia de imágenes incluye una identidad opaca del cargador y
del objeto de archivo; un hash por ruta solamente no identifica el mapping vivo.
La observación resume ese inventario comprobado mediante un SHA-256 canónico y
una revisión monotónica del cargador. El contrato del puerto exige detectar una
carga/descarga aunque el conjunto final vuelva a coincidir. Imágenes externas
requieren clasificación y evidencia explícitas; las bibliotecas del sistema no
se consideran acreditadas por el inventario del bundle.

La identidad de proceso contiene PID, nacimiento obtenido del sistema operativo
con resolución suficiente y un nonce de 128 bits generado por el proveedor al
iniciar. El nonce no procede de Request.session. Época host y generaciones de
PINE/VU/GS son independientes; cero o agotamiento rechazan el intervalo. Los
tokens de worker acreditan lifecycle, no por sí solos retención ni exclusión.

El adaptador futuro debe tomar y revalidar esos datos dentro del alcance CPU y
del coordinador, antes y después del muestreo, y comprobar el peer del transporte.
Ante fallo, reinicio, sustitución, dependencia desconocida, cambio del cargador o
identidad inaccesible, retorna `None`/`IdentityUnavailable`; no reconstruye una
observación a partir de afirmaciones del cliente. El modelo no pretende resistir
un proceso malicioso que manipule su propio código/memoria; ese caso queda fuera
del alcance de estas comprobaciones de integridad y ciclo de vida.

`DiagnosticGuard` es de un solo uso: `idle → observing → complete`, o `discarded`.
`begin()` guarda únicamente la identidad verificada por el puerto. `finish()`
recibe los hechos AP obtenidos por el adaptador CPU y vuelve a consultar el puerto;
solo entonces devuelve un informe diagnóstico inmutable. Cambiar cualquiera de
las identidades o perder el puerto descarta el resultado. El módulo no fabrica
los hechos AP ni los obtiene de configuración guardada. Un nuevo intento requiere
otra instancia, otro alcance de observación y nuevas comprobaciones.

## Tareas y aceptación

1. **IP-1 / IP01–05:** inventariar identidades presentes y ausentes con testigos
   de fuente/build; registrar la decisión del puerto y sustitución/reinicio.
2. **IP-2 / IP06–07:** publicar la matriz de dieciocho hechos; separar restricciones
   estáticas, estado runtime no observado y capacidades concedidas (ninguna).
3. **IP-3 / IP03–09:** implementar y probar el consumidor diagnóstico con dobles,
   sin modificar la ruta de captura. Verificar CI Python y custodia reproducible.
4. **IP-NATIVE (pendiente):** implementar el adaptador macOS con pruebas del proceso
   propio, inventario real y notificaciones del cargador; después integrarlo en una
   nueva copia privada del proveedor. La firma ad hoc, `ps` y `lsof` son indicios
   auxiliares; no sustituyen esa integración ni los gates de exclusión.
