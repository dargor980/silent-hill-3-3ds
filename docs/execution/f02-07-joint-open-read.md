# F02.07 / LP-C — Catálogo, apertura y recorrido conjunto

Fecha: 2026-10-18. Fuente: SRC64. Contrato:
[JR01–JR08](../../schemas/joint-open-read-v1.md). Evidencia:
[metadatos públicos](../compatibility/joint-open-read-evidence.json).

## Resultado y alcance

Se implementó `joint_open_read.reconcile_joint_open_read`: once pausas y 81
solicitudes regionales enlazan selección, apertura, descriptor finalizado y las
siete pausas de finalización/copia de SRC63. No modifica CA/CP ni recodifica sus
paquetes. La política predeterminada rechaza continuidad no demostrada; el modo
diagnóstico explícito entrega consistencia con cero `Read`, vínculos y capacidades.

La investigación privada confirmó que la apertura posiciona el objeto en el
offset del recurso antes de finalizar el descriptor. Se contrastaron tres
ventanas de 796 bytes y 17 instrucciones fijadas; además se reverificaron trece
ventanas de los perfiles anteriores. El posicionamiento modifica la posición,
sin llenar la caché. Esto describe el perfil estático, no una ejecución observada.

## Composición y límites

La última pausa CA conserva sus cinco rangos e incorpora raíz, pool completo y
vtable. El pool observado ocupa 792 bytes para 16 filas; el contrato admite hasta
84 filas dentro del máximo de 4.096 bytes por rango. Su cabecera y fila seleccionada
se comparan directamente con los rangos CP originales. No se generan observaciones
artificiales para dividirlo ni se exige que las filas ajenas permanezcan iguales.

Se exige handle coincidente con el descriptor, fila inicial completa, generación,
posición, caché inválida y flags compatibles. Se verifican identidad, backing y
páginas a lo largo de las once pausas, no solo dentro de cada mitad. Buffer y destino
tampoco pueden solaparse físicamente con controles de catálogo/apertura.

El adaptador mantiene responsabilidades separadas: CA valida catálogo y apertura;
CP valida backend, buffer, copia y retorno; JR valida la unión y su política de
evidencia. Usa modelos existentes, funciones puras y biblioteca estándar. No añade
dependencias, acceso a archivos, lógica de adquisición ni cambios al runtime.

Los estados suministrados no demuestran ausencia de cierre, reasignación,
restauración o escrituras ajenas entre pausas. El subconjunto sigue requiriendo
aceptación anterior al progreso del worker. El snapshot privado disponible tiene
cero objetos activos y no sirve como inicio anterior a la carga.

## Reproducibilidad y validación

Dos análisis estáticos produjeron informes idénticos de 2.677 bytes, SHA-256
`5cb75ab2d55a761bd84bdb29a67eb4dfb58693f1cdacee6828482591bfa1cc8d`.
Se reverificaron ISO, ejecutable, catálogo, contenedor, recurso y sector válido.
El plan privado se creó sin sobrescritura, directorio 0700 y archivo 0600; se
cerraron lectores antes de publicar y las fuentes leídas permanecieron intactas.

La primera ejecución detectó un desplazamiento incorrecto en el generador de
paquetes propios del test de backing: 21 casos pasaron y uno falló antes de detenerse.
Se corrigió únicamente ese generador; no se debilitó el contrato. Después pasaron
44 casos. La revisión añadió cinco casos: límites de 84/85 filas, flags asíncronos
y mitades válidas por separado pero con sesión/backing distintos. Resultado:
**49 pruebas específicas aprobadas**, cobertura nueva de 65/65 líneas y 16/16 ramas.

La regresión completa aprobó **3.096/3.096 pruebas**, sin fallos, errores ni
omisiones. Cobertura total: 5.303/5.348 líneas y 1.449/1.482 ramas; gate 80/80
aprobado. Ruff y formato aprobados para 137 archivos; controles del repositorio
con cero errores. Hashes, custodia, enlaces y diff comprobados; entradas fijadas
de SRC55–SRC63 intactas.

La CI existente descubre automáticamente el nuevo módulo y las pruebas Python;
continúan los gates de custodia, trazabilidad, lint y cobertura 80/80. No se ejecutó
CI remota, compilación C++/3DS, nueva sesión PCSX2 ni consola física en esta unidad.

## Tareas y siguiente unidad

- [x] **JR-T1 / JR01,04,05:** apertura, posicionamiento y perfil privado contrastados.
- [x] **JR-T2 / JR02–07:** composición original, pool, mapas y política cerrada.
- [x] **JR-T3 / JR08:** análisis duplicado, permisos, fuentes y publicación privada.
- [x] **JR-T4 / JR08:** regresión completa, gates y trazabilidad de resultados.

1. **Observación de continuidad:** localizar escrituras de liberación, asignación
   y generación del objeto seleccionado y definir cobertura desde apertura hasta
   retorno. Entregables: EARS, perfil de eventos, guardia de sesión/reset/restauración
   y fixtures con pérdida de eventos, reciclaje y huecos. Aceptación: ninguna
   continuidad acreditada solo por coincidencia de extremos o ausencia de eventos
   sin prueba de cobertura; los rechazos deben conservarse.
2. **Progreso temprano del worker:** situar una observación interna anterior a
   publicar/ejecutar la solicitud o ampliar el contrato con una relación causal
   verificable. Entregables: perfil y casos de worker adelantado, éxito, error y
   cancelación; conservar las negativas actuales hasta justificar el nuevo alcance.
3. **Descubrimiento y captura LP-D:** obtener punteros de la sesión bajo guardia,
   contabilizar estados, sondeos e hits y fijar presupuesto completo. Los once
   estados/81 solicitudes aún excluyen esos costes; integrar sondeos intercalados
   requiere extender el contrato sin omitir ni renumerar evidencias. Iniciar antes de la carga en
   español/Normal/Normal, sin restaurar entre puntos; ≤48 estados, ≤256 solicitudes/
   hits, 60 segundos activos, 3.600 de pared, 8 GiB de etapa y 10 GiB libres.
   Exigir cierre de lectores, custodia y dos reimportaciones iguales.

F02.07/Q05/G02, procedencia real, semántica de cámara, dos salas conectadas y
validación en New Nintendo 2DS XL permanecen pendientes.
