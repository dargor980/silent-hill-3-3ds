# Vectores comunes de PD v2

Vectores sintéticos independientes del codec. Mantienen los campos de los
vectores [v1](../platform-diagnostic/README.md), cambiando solo el magic a v2.
Los cuatro vectores `counts-*` fijan además los dos u32 little endian en offset
236: total 1.025, demanda observada 1.069 y dos repartos del límite 2.048.
Los usan C++ y Python; v1 se conserva para probar incompatibilidad.
