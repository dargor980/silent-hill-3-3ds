# Vectores PD v1 propios

Hexadecimal ASCII sin bytes de PCSX2 ni del juego. Generados independientemente
del encoder C++ con `struct.pack` little endian según `schemas/platform-diagnostic-v1.md`.

- Solicitud: `SH3PDQ01`, desafío bytes 1..16, secuencia `0x0102030405060708`.
- Observación: `SH3PDR01`, cabecera `[1,2,1,1,0,0,0,0]`, la correlación anterior;
  PID `0x12345678`, nacimiento `0x1020304050607080`, nonce bytes 17..32;
  cinco hashes de 32 bytes repetidos (1, 2, 3, 4, 5), revisión `0x0807060504030201`,
  conteos 26/621, hechos `[0,1,2]` repetidos seis veces, épocas 11/12/13/14.
- Rechazo: misma correlación, cabecera `[2,0,0,0,6,0,0,0]` y 254 ceros de payload.

C++ verifica igualdad byte por byte; Python verifica semántica y perturbaciones.
Los vectores son sintéticos, no evidencias de identidad ni de un canal autenticado.
