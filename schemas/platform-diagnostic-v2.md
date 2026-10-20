# PD v2 — Diagnóstico con capacidad de 2.048 imágenes

Extiende [PD v1](platform-diagnostic-v1.md) para [LC](image-capacity-v2.md).
Conserva PD01–PD08, tamaños, offsets, perfil PT v2, correlación, evidencias,
hechos/épocas y rechazo sin payload. No cambia autenticación ni concede captura.

- **PD2.01:** WHEN se codifique o decodifique una solicitud THEN SHALL exigir
  el magic ASCII `SH3PDQ02`. IF recibe `SH3PDQ01` u otra versión THEN SHALL rechazarla.
- **PD2.02:** WHEN se codifique o decodifique una respuesta THEN SHALL exigir
  `SH3PDR02`, incluidos rechazos. SHALL NOT reinterpretar respuestas v1 como v2.
- **PD2.03:** WHEN una respuesta contenga inventario THEN SHALL exigir entre
  1 y 2.048 imágenes de aplicación y entre 0 y `2048 - application` de plataforma.
  La resta SHALL comprobarse solo después de validar aplicación, evitando overflow.
- **PD2.04:** WHEN dos extremos difieran de versión THEN SHALL cerrar por error
  de protocolo sin negociación, fallback, reajuste remoto ni muestras aceptadas.
- **PD2.05:** WHEN se pruebe THEN SHALL usar vectores comunes C++/Python para
  1.025, 1.069, 2.048 y exceso, además de los controles anteriores.

No se altera la identidad PT v2 ni los dominios de sus digests: ampliar un límite
de cantidad no cambia los campos canónicos. Los magics fijan el contrato wire;
el lanzador conserva sus hashes de política y manifiesto explícitos. Un candidato
v1 archivado exige su consumidor histórico fijado y no se ejecuta con v2.
