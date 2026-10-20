# F02.07 / LP-C — Diagnóstico de admisión

Fecha: 2026-10-18. Fuente: SRC71. Contrato [AP01–AP08](../../schemas/admission-profile-v1.md).
Evidencia: [metadatos públicos](../compatibility/admission-profile-evidence.json).

## Resultado

Se incorpora un evaluador puro y un sampler interno del proveedor, sin entradas
del cliente. El resultado separa incompatibilidades observadas de condiciones
desconocidas. No es un permiso, no crea conexiones ni arma LifetimeGuard.
**Ningún modo de ejecución queda admitido.**

El sampler comprueba primero una marca local al hilo, activada solo al terminar
la inicialización CPU y retirada al comenzar el cierre. Una llamada desde otro
hilo retorna antes de leer configuración/punteros compartidos. Execute conserva
otra marca mediante RAII durante cambios de implementación, ejecución normal,
reentrada y unwinding de excepciones. Esto no establece exclusión entre hilos.

El evaluador usa almacenamiento fijo, no depende de tipos PCSX2 ni modifica estado.
El adaptador privado traduce hechos del proveedor. LifetimeGuard, HostEpoch y el
puente de escrituras conservan sus versiones SRC70. Esta separación mantiene
responsabilidades y permite probar la política sin emulador ni originales.

## Matriz verificada en la fuente fijada

Proveedor: `fd9d310ccbb6b8b62c976da8886a3c8fd3a10ff3`. Se conserva la copia SRC70
y se genera otra copia privada con cambios en VMManager.cpp/.h y lista CMake.
El CMake público anterior se guarda como snapshot para comprobar su evidencia.

| Condición | Comprobación | Límite |
|---|---|---|
| Hilo CPU | Marca local tras CPUThreadInitialize | No autentica una llamada de red ni sustituye la disciplina del host |
| Fuera de Execute | Ámbito que restaura el valor anterior | No certifica otras transiciones ni otros escritores |
| Pausa | Estado Paused | SetState publica Paused antes de esperar VU/GS |
| Cambio de implementación | Flag interno sin cambio pendiente | Debe comprobarse bajo futura exclusión |
| EE/IOP/VU0/VU1 | Opciones de recompiler apagadas y puntero al intérprete esperado | Nulos, otras implementaciones y replayer se rechazan |
| Caché EE / fastmem / MTVU | Opciones desactivadas | Conservador incluso si una opción no tiene efecto en una plataforma |
| VIF dinámico | Constante de compilación | Es true en la fuente fijada; impide satisfacer este perfil inicial |
| RAIntegration | Consulta interna real | Backend Windows no ejecutado en este lote |
| PINE | Configurado o inicializado implica incompatibilidad | Ambos falsos dejan desconocido: Deinitialize publica fin antes del join |
| RDebug / otros escritores | Desconocido | Ausencia de llamadas en una inspección no prueba exclusión en el binario |
| GS / VU drenados | Desconocido | Paused, IsOpen o IsDone no son una barrera de nuevos trabajos |

En particular, elegir intérprete EE no desactiva automáticamente VIF dinámico.
No se ha cambiado ese comportamiento del proveedor. La política no ofrece una
ruta alternativa de aceptación ante datos ausentes o valores de enum inválidos.

## Validación y alcance

Cuatro objetos reales: VMManager y PINE en ON/OFF con Apple Clang 21, x86_64,
C++20, ThinLTO y SDK explícito. La interfaz del sampler desaparece en OFF. No se
configura ni enlaza de nuevo PCSX2 completo; el ajuste de lista CMake se inspecciona.

El [harness](../../tests/fixtures/pcsx2-admission-profile/README.md) ejecuta
34 escenarios en cuatro modos: ON, OFF, ASan/UBSan y funciones anteriores OFF.
Resumen de efectos `df3df8e1e5d72d1b`. Subsistemas, CPU, configuración y estado
de PINE son dobles; no equivale a ejecutar trabajadores reales o una VM.
Los seis tests portables comprueban defaults, máscaras por condición, 262.144
subconjuntos, valores inválidos, independencia entre llamadas y uso concurrente.

La regresión aprueba **81 pruebas C++ por configuración** (Debug, Release y
ASan/UBSan) y **3.096 pruebas Python**, sin fallos ni omisiones. La medición LLVM
del evaluador y su cabecera alcanza **100 % de líneas y ramas**; no mide PCSX2
completo. Python mantiene 5.303/5.348 líneas (99,16 %) y 1.449/1.482 ramas
(97,77 %). Los gates permanecen en 80 %. Ruff, formato de 137 archivos del
alcance CI, comprobaciones del repositorio y `git diff --check` pasan.

Se conservan los intentos iniciales: OFF y anterior OFF fallaron por dos
variables sin uso en los dobles propios, corregidas con `maybe_unused`.
La primera medición detectó 50 % de ramas en la cabecera porque los casos de
límite se evaluaban como constantes; se añadieron valores dinámicos y se repitió
la suite C++ y la medición. No se redujeron warnings ni umbrales de cobertura.

Dos auditorías idénticas de **12.993 bytes**, SHA-256
`78f78371a5dd37944677b7f25b4bc64a36a7d96dc894d29d758924db913f4199`,
comprueban fuentes previas, snapshots, parche, fragmentos, objetos, ejecutables
y recibos supervisados. La nueva suite participa en los presets host y cobertura
pública existentes, sin originales. CI remota, GCC de CI y consola no se ejecutan.

## Siguiente unidad: exclusión de efectos (AD-2)

El siguiente protocolo debe demostrar cada fase antes de habilitar AP/armado:

1. Despachar la operación a una frontera CPU fuera de Execute y de transiciones
   de reset/configuración/carga. No mantener un lock PINE mientras se espera CPU.
2. Cerrar la entrada de nuevos accesos de memoria PINE y esperar los ya iniciados.
   Clasificar aparte comandos que encolan trabajo CPU; cancelar/rechazar solicitudes
   tardías sin ciclos de espera. `s_end` solo no acredita que el hilo terminó.
3. Impedir nuevos productores y drenar VU, después GS, antes de adquirir un lock
   que esos trabajadores necesiten. Probar cierres, errores y cancelación. Una
   instantánea de la cola vacía no constituye una sección exclusiva.
4. Proteger efectos de memoria y transiciones durante adquisición de extremos;
   fijar el orden de locks antes del mutex de avisos. Los callbacks no deben
   despachar ni esperar al CPU/GS/PINE mientras mantienen ese mutex.
5. Releer perfil, sesión, época y anclas dentro de esa sección. Mantener como
   desconocidas las rutas sin exclusión demostrada. Probar escritor que empieza
   antes, durante y después, reentrada y recuperación; solo entonces unir AD-3.

Esta secuencia es un diseño pendiente de integración y ensayos adversarios,
no una prueba de ausencia de deadlocks. AD-4 cubrirá funciones pendientes,
enlace/ejecución completos y coste. LG-I2–I4, LP-D, F02.07/Q05/G02 permanecen abiertos.
