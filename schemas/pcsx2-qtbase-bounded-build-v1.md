# QL v1 — Intento acotado de compilación de Qt Base

Complementa [QB01–QB08](pcsx2-qtbase-v1.md) para
`prerequisites/dependencies-qtbase/build-and-validate`. SRC39 conserva la
preparación histórica y su decisión de no iniciar por falta de reserva.

## Decisión de capacidad

La reserva de 20 GiB de IB02 es una política genérica, no un tamaño medido.
Este intento tiene un alcance conocido: Qt Base 6.11.1 MinSizeRel para una
arquitectura, sin ejemplos ni suite completa, 1.170 órdenes de compilación,
sin WebEngine ni módulos Qt adicionales. El build preparado ocupa unos
54 MiB asignados y el volumen dispone de 18,22 GiB. Esos datos no predicen
el tamaño final; permiten ensayar un presupuesto independiente con parada.

Se sustituye **solo para este intento de Qt Base** el umbral de inicio de
QB03/IB02 por los límites QL01/QL02. No se reutiliza la excepción Shaderc.
El evaluador general IB conserva 20 GiB para PCSX2 completo; MoltenVK y las
dependencias restantes requieren su evaluación propia. No se autoriza ampliar
límites automáticamente ni borrar archivos para alcanzarlos.

## Requisitos EARS

- **QL01 — Inicio.** ANTES de compilar, el coordinador DEBERÁ comprobar los
  insumos de SRC39, disponer de 18 GiB libres, fijar dos jobs y colocar los
  temporales del compilador dentro del build medido. DEBERÁ conservar opciones,
  fuentes, prefijo y arquitectura definidos en QB.
- **QL02 — Parada.** MIENTRAS compile, el coordinador DEBERÁ muestrear espacio
  y tamaño lógico/asignado del build con pausa nominal de un segundo entre
  muestras. SI cualquiera de los tamaños supera 4 GiB, el espacio libre baja
  de 12 GiB o falla la medición, DEBERÁ terminar su grupo de procesos, conservar
  el resultado y omitir instalación. DEBERÁ evaluar también la muestra final.
- **QL03 — Verificación del control.** ANTES del build real, el procedimiento
  DEBERÁ comprobar con procesos sintéticos éxito, salida fallida, falta de
  reserva inicial y parada por tamaño/espacio simulado/error de medición.
  DEBERÁ comprobar que un proceso hijo del grupo también termina. No DEBERÁ
  llenar el disco ni afectar procesos ajenos para probar esos caminos.
- **QL04 — Evidencia.** CUANDO termine, el coordinador DEBERÁ conservar límites,
  tiempos, muestras, máximos/mínimos, motivo de parada, salida y log. DEBERÁ
  declarar que el muestreo no impone una cuota ni observa todos los picos.
- **QL05 — Aceptación.** SI el build termina dentro del presupuesto, el
  procedimiento DEBERÁ ejecutar QB04–QB07 antes y después de instalar y
  conservar fallos/correcciones. CUANDO publique resultados, DEBERÁ repetir
  CMake PCSX2/gate con IB02 general y mantener explícitas las dependencias
  posteriores y pruebas no realizadas.

## Diseño y tareas

Medición, política de límites y administración del proceso están separadas.
El coordinador local recibe una función de medición; las pruebas sustituyen
solo esa función para simular espacio insuficiente. La terminación utiliza
el grupo creado por el coordinador, SIGTERM y después SIGKILL si fuera preciso.
El límite de 4 GiB deja aproximadamente 14 GiB libres desde el mínimo de
inicio, antes de actividad ajena; la segunda condición añade protección frente
a esa actividad. No es garantía de capacidad futura ni de picos entre muestras.

1. Verificar insumos y preparar coordinador y ensayos sintéticos (QL01/QL03).
2. Ejecutar el build vigilado a dos jobs y conservar resultado (QL02/QL04).
3. Probar herramientas, seis casos propios y dos programas originales;
   instalar solo tras éxito, repetir consumidores e inventarios (QL05/QB07).
4. Repetir configuración PCSX2/gate, documentar diferencias y siguiente unidad.
