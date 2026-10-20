# F02.07 — Enlace del transporte PINE reparado (SRC88)

Fecha: 2026-10-18. Continúa [SRC87](f02-07-pine-joint.md) y completa
IW-PINE-JOINT3 bajo [PJ09–PJ10](../../schemas/pine-joint-v1.md).
El informe anterior conserva el bloqueo de capacidad observado entonces.

## Resultado

La fuente privada pine-transport v2 compila y enlaza la aplicación completa:
825 entradas, catorce fuentes propias, en 347,658 s. El observador está activado
y las excepciones siguen habilitadas solo para cooperative_gate.cpp. No se
modifica código adicional ni se crea otra copia de fuente: permanecen veintidós.

La ejecución inicia con 20,91 GiB libres, dos jobs y supervisión IB02: reserva
inicial de 20 GiB, suelo de 10 GiB y límite de etapa de 8 GiB. La capacidad
liberada por el usuario permite completar esta tarea; los recibos anteriores
que registraban capacidad insuficiente se conservan.

Los dos programas CTest originales pasan: **31 tests common y 82 core, 113 en
total**. Se conservan JUnit y logs. Los sanitizadores y las 63 pruebas PINE de
SRC87 no se repiten porque sus fuentes y entradas permanecen intactas; tampoco
se atribuyen esos resultados a una sesión VM.

## Bundle y prueba de arranque

El postproceso del proveedor devuelve éxito del build pero registra errores de
firma: el ejecutable/bundle original contiene un componente MoltenVK sin firmar.
Ese bundle y su log quedan intactos. Por tanto, el exit code del build no se usa
como prueba de distribución lista para ejecutar.

Una copia candidata privada corrige rutas/identidad de dependencias y firma
ad hoc sus componentes. La verificación estricta y profunda pasa para **200
archivos y 42 Mach-O x86_64**. No quedan rutas de dependencia hacia el checkout
ni el prefijo del usuario. Se comprueba por hash que el bundle original y los
5.228 archivos del prefijo de dependencias se conservan.

El candidato ejecuta `-testconfig` con un perfil privado nuevo: **13,861 s,
salida cero y cierre de procesos verificado**. No se solicita juego, BIOS ni
ISO. No se reemplaza la aplicación instalada. La firma ad hoc acredita esta
copia local, no notarización ni distribución pública.

## Custodia y continuación

La evidencia liga fuente, compilación, recibos, recursos supervisados, candidato
y perfil por hash. Verifica las entradas públicas/históricas SRC87 y vuelve a
comparar las tres últimas fuentes. Las veinte fuentes anteriores fueron
verificadas por SRC87; no se presenta eso como una nueva repetición de su auditoría.

IW-PINE-JOINT1–3 queda cerrada en el alcance de herramienta host probado. F02.07,
CQ3-C/D, CQ-4 y AD-3 siguen abiertos. La admisión permanece vacía: ni enlace,
ni testconfig, ni firma prueban exclusión global o ejecución en Nintendo.

La siguiente unidad RD-T1–3 comprueba ausencia de RDebug en este artefacto
concreto: fuentes efectivamente compiladas, objetos/archivos del enlace,
dependencias y símbolos con controles positivos/negativos. Su resultado será
diagnóstico, pendiente de vincularlo a la identidad del proceso real y de
resolver los otros escritores/backend.
