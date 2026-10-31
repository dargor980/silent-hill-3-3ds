# HMN v1: movimiento nativo de inspección de Heather

## Alcance y decisión (2026-10-29)

El usuario solicita posponer la búsqueda de pared 60/hueco 14/60 y avanzar
con los datos existentes. HM-T2b permanece parcial: no se declara resuelta
la física general de PS2. Este perfil permite construir el controlador de
una escena acotada sin depender de más navegación manual en PCSX2.

Fuentes: [productores y contactos observados](../docs/execution/f06-01-heather-movement-profiles.md)
y [límite de la búsqueda hasta C148](../docs/execution/f06-01-heather-wall60-access.md).
Las muestras de caminar/correr dan 28/70 unidades por actualización; el
giro observado es aproximadamente ±0,088 radianes. El escritor usa la
orientación anterior al giro. Se conservan estas magnitudes y ese orden,
sin afirmar identidad bit a bit con EE/VU, aceleración universal ni metros.

## Requisitos EARS

- **HMN01** WHEN recibe un estado válido, intención admitida y dos ticks PAL
  THEN el planificador SHALL producir una propuesta de posición, orientación,
  ordinal y matriz de instancia, sin modificar el estado de entrada.
- **HMN02** WHEN planifica espera, caminar o correr THEN SHALL proponer
  respectivamente 0, 28 o 70 unidades horizontales según el yaw anterior;
  SHALL conservar Y. WHEN gira THEN SHALL actualizar el yaw después del
  desplazamiento, con signo negativo a izquierda y positivo a derecha.
- **HMN03** IF recibe valores no finitos, estado fuera de límites, intención
  desconocida, ticks distintos de dos, ordinal agotado o salida fuera de
  límites THEN SHALL devolver un error sin modificar ningún byte de salida.
- **HMN04** WHEN genera la matriz THEN SHALL representar `T(posición)·Ry(yaw)`
  en columnas, escala unitaria y fila afín `(0,0,0,1)`. SHALL NOT incorporar
  pose local, centro de malla, normalización de visor ni traslación de raíz.
- **HMN05** WHEN una aplicación consume la propuesta THEN SHALL resolver
  contactos por separado y publicar posición, pose HL y matriz solo después
  de validar toda la actualización. Un fallo SHALL conservar el estado
  publicado. La propuesta libre SHALL NOT presentarse como respuesta física.
- **HMN06** WHEN se repite la misma secuencia de intenciones por tick a
  diferentes cadencias de presentación THEN SHALL obtener el mismo resultado
  en la misma plataforma. WHILE está pausado o suspendido THEN la aplicación
  SHALL omitir actualizaciones y descartar tiempo de suspensión.
- **HMN07** WHEN integra el módulo THEN SHALL ejecutar pruebas Release y
  ASan/UBSan y exigir ≥80 % de líneas y ramas del módulo en CI. La compilación
  ARM SHALL distinguirse de ejecución en consola.

- **HMN08** WHEN actualiza un actor inicializado THEN el coordinador SHALL
  validar movimiento y selección HL antes de consultar contactos. SHALL
  mapear idle/walk/run a 101/109/113 sin transiciones implícitas. IF HL
  rechaza la selección THEN SHALL conservar el estado completo y no llamar
  al resolvedor ni leer muestras.
- **HMN09** WHEN consulta contactos THEN SHALL pasar posición previa,
  posición propuesta y ordinal nuevo en unidades originales. IF el puerto
  no está disponible, no soporta la consulta, devuelve estado desconocido
  o no escribe XYZ finitos y acotados THEN SHALL rechazar la actualización.
- **HMN10** WHEN el puerto acepta XYZ THEN SHALL conservar esos tres valores,
  incluidos cambios verticales, y reconstruir la matriz con el yaw propuesto.
  SHALL evaluar ambos canales HL en almacenamiento provisional y publicar
  solo tras su éxito. SHALL conservar las matrices de hueso en espacio de
  modelo, separadas de la matriz de instancia.
- **HMN11** WHEN inicializa o reinicia THEN SHALL preparar espera en muestra
  cero, ordinal cero y la colocación explícita sin consumir ticks ni consultar
  contactos. IF falla THEN SHALL conservar estado y disponibilidad previos.
  La aplicación SHALL comprobar la colocación de entrada de la escena antes
  de inicializar; este reinicio no acredita un spawn libre de colisión.
- **HMN12** WHILE ejecuta una llamada THEN los callbacks SHALL observar solo
  la instantánea publicada anterior. IF intentan reentrar mediante reset o
  step THEN SHALL recibir busy sin modificarla. Las llamadas y lectores
  SHALL pertenecer a un único hilo; no se promete sincronización entre hilos.

HMN01–06/08–12 refinan HM05; HMN03/07 refinan HM06. HMN05 se implementa
en HM-T3c; la gestión de tiempo de HMN06 se implementa en HM-T3d.

## Contrato numérico y API

`InspectionMovementState`: posición XYZ en unidades originales, yaw en
radianes, ordinal `uint32_t` de actualizaciones publicadas. Cada componente
de posición debe ser finita y estar en `[-1000000,1000000]`; el límite es
una guarda del runtime, no un límite descubierto del juego. Y es libre
dentro de ese intervalo: no se aplana al suelo.

Yaw válido: `[-pi_f,pi_f)`, con `pi_f=3.14159265358979323846F`.
`InspectionMotion`: idle/walk/run; `InspectionTurn`: none/left/right.
El perfil no acepta retroceso, desplazamiento lateral, salto ni analógico.

Una llamada representa exactamente 40 ms de simulación (dos ticks de
1/50 s), con intención ya muestreada. No recibe reloj de pared, frame del
render ni botones SDK. No recupera pasos perdidos automáticamente.

1. Validar estado, intención, ticks y ordinal, en ese orden.
2. `d = (sin(yaw)*paso, 0, cos(yaw)*paso)`. En espera se usa cero exacto.
3. `p' = p+d`; Y se copia. Rechazar coordenadas fuera de límites.
4. `yaw' = yaw + giro`, giro `-0.088F`, `0` o `0.088F`; normalizar con una
   suma/resta de `2*pi_f` al intervalo semiabierto. El cruce se define para
   este perfil nativo; el cruce exacto original sigue sin verificar.
5. Construir matriz con la posición nueva y yaw nuevo. Incrementar ordinal
   una vez y asignar la propuesta completa al final.

Salida `InspectionMovementPlan`: `next`, `displacement` y `model`.
`displacement` es el delta solicitado, no la resta redondeada de posiciones
ni una corrección de contacto. `next` puede aliasar la entrada si se reutiliza
un plan: toda lectura precede a su publicación. La matriz es provisional
hasta resolver contactos; cualquier corrección posterior exige reconstruirla.

Se usa `float` binario de 32 bits, sin fast-math ni contracción de expresiones
en esta unidad. Las funciones trigonométricas son las de la plataforma.
No se promete igualdad bit a bit host/ARM ni se reproduce el microajuste
sin contacto de PS2. Vectores de prueba analíticos en doble precisión:
tolerancia absoluta `0.01` unidades y `1e-6` para matriz rotacional por paso
en el rango de muestras; no amplía los umbrales de las auditorías originales.

## Separación de responsabilidades y pruebas

El dominio planifica; el puerto de contactos recibe el segmento en
coordenadas originales y devuelve una posición aceptada. La aplicación
coordina ese resultado con HL y construye la matriz final. Cámara y render
solo consumen el estado publicado. No hay recursos, archivos, memoria de
PCSX2, SDK ni asignaciones dinámicas en el planificador (SRP/DIP).

Vectores mínimos: yaw 0 y ±pi/2, los tres movimientos y giros, giro en
espera, traslación antes del giro, conservación de Y, ambos cruces de yaw,
matriz aplicada una vez a un punto asimétrico; NaN/Inf en cada campo,
coordenadas y yaw límite, enums inválidos, ticks 0/1/3/máximo, ordinal
máximo, desborde de posición y salida intacta byte a byte. Replay de las
mismas intenciones con presentación regular e irregular y sin actualización
durante pausa. Oráculo trigonométrico analítico separado de la implementación.

## Coordinación HM-T3c

`ports::IMovementContacts::resolve(query, accepted)` es una consulta const,
sin efectos de gameplay ni consumo irreversible: una animación posterior
puede fallar y requerir repetirla. El mundo consultado permanece estable
durante la llamada. El adaptador concreto debe validar geometría, alcance
físico y configuración de colisión; este puerto no demuestra que una
posición aceptada arbitraria sea físicamente alcanzable. No existe un
adaptador de producción que acepte todo silenciosamente.

Query: XYZ anterior, XYZ solicitado y ordinal propuesto. La salida se
inicializa con NaN para detectar respuestas no escritas o parciales. Los
estados son accepted/unavailable/unsupported; cualquier otro valor se
rechaza. Se admite corrección Y y bloqueo total, sin sumar otra vez el
delta solicitado. Una aceptación no depende de que la posición cambie.

`application::InspectionActor` conserva perfil y topología propios, y
referencias a lector y puerto con vida mayor que el actor. Su instantánea
solo es legible y contiene movimiento, estado HL y matriz de instancia.
Un almacenamiento provisional persistente evita objetos grandes en la
pila por actualización; presupuesto total del coordinador ≤32 KiB, sin
asignaciones dinámicas. Los callbacks pueden observar, pero no publicar.

Orden: comprobar inicialización → proponer movimiento → prevalidar selección
HL → consultar contacto → validar XYZ y reconstruir matriz → evaluar HL
en copia → publicar instantánea. Errores indican etapa y, cuando corresponde,
detalle del núcleo. La copia final no lanza excepciones; no es un primitivo
atómico para lectores concurrentes. Reset prepara espera y una colocación
comprobada por su llamador, sin consumir ticks.

Se reutiliza la evaluación HL sin modificar sus huesos con coordenadas
mundiales. El futuro renderer debe aplicar la matriz de instancia una sola
vez al resultado de la pose. Un bloqueo de posición no cancela la animación
seleccionada por intención. Un error transition_busy no avanza ni movimiento
ni mezcla: el presentador HM-T3d conserva la intención pendiente y sigue actualizando
el objetivo vigente hasta que pueda cambiar. No se añaden colas ocultas aquí
ni se transforma idle→run en una transición que HL no ha verificado.

Pruebas HM-T3c: fallos del puerto y XYZ inválidos/parciales; callbacks que
leen la instantánea y reentran; fallo de cada lectura de ambos canales en
inicialización, mezcla y salida; reintento equivalente a una ejecución sin
fallos; corrección vertical, bloqueo, raíz local no nula y matriz final con
traslación única; copia de topología, máximo de huesos y memoria constante.

## Controles y tiempo HM-T3d

- **HMN13** WHEN recibe un intervalo de juego válido THEN el presentador
  SHALL acumular microsegundos enteros y ejecutar un paso de dos ticks por
  cada 40.000 µs, conservando el resto menor de 40.000. SHALL limitar una
  llamada a tres pasos. IF el intervalo supera 120.000 µs THEN SHALL
  descartarlo entero junto al resto y la solicitud pendiente, sin simular.
- **HMN14** WHEN cambia la intención durante una mezcla THEN SHALL conservar
  la última intención, sustituyendo la anterior, y continuar el objetivo
  vigente hasta terminar la mezcla. WHEN solicita carrera desde espera THEN
  SHALL recorrer explícitamente espera→caminar→correr, sin alterar HL.
- **HMN15** WHEN procesa controles THEN SHALL priorizar salida, liberación
  pendiente, pausa, reinicio, paso manual y reproducción, en ese orden.
  El paso manual SHALL ejecutar como máximo una actualización y solo estando
  pausado. Pausa, paso y reinicio SHALL consumir el intervalo de esa llamada.
- **HMN16** WHEN suspende o termina THEN SHALL borrar deuda temporal y
  solicitud pendiente. WHEN regresa de suspensión THEN SHALL conservar el
  estado de pausa anterior y exigir una muestra sin botones; SHALL descartar
  también el tiempo de esa muestra. SHALL exigir esa liberación al iniciar,
  cambiar pausa, reiniciar o fallar una actualización. START SHALL funcionar
  incluso durante esa espera; el estado detenido SHALL ser terminal.
- **HMN17** IF un paso falla THEN SHALL detener el lote, conservar la última
  instantánea completa, pausar y borrar deuda/solicitud. Los pasos anteriores
  correctos del mismo lote SHALL permanecer publicados. Un reintento SHALL
  requerir nueva acción explícita, sin recuperar el tiempo descartado.
- **HMN18** WHEN traduce controles 3DS THEN SHALL usar cruceta ↑ para avanzar,
  ←/→ para girar, B mantenido para correr, A para pausa, R para paso, L para
  reinicio y START para salida. Acciones discretas SHALL depender de flancos;
  teclas opuestas SHALL cancelarse. ↓ solo y analógico SHALL NOT crear
  retroceso. Cualquier botón SHALL participar en la guarda de liberación.
- **HMN19** WHEN traduce el reloj ARM11 THEN el adaptador SHALL conservar el
  residuo de conversión a microsegundos y restablecer su base tras cambios
  de ciclo de vida. IF el reloj retrocede o el intervalo es excesivo THEN
  SHALL descartar la deuda sin desbordar la multiplicación. Hooks duplicados
  SHALL NOT cambiar el estado ni reiniciar un reloj ya reanudado.

HMN13–19 refinan HMN06 y HM05–06. Son reglas nativas de inspección, no
atribuciones nuevas al mando, temporización o física original PS2.

`MovementController` posee `InspectionActor`, su ciclo de vida y la
colocación inicial validada. Devuelve cuántos pasos publicó cada llamada;
no renderiza ni consulta un reloj externo. La instantánea permanece de solo
lectura. Las llamadas reentrantes desde callbacks no producen efectos.
Memoria total fija ≤32 KiB. Reset exitoso conserva si estaba pausado; un
reset fallido conserva el actor y deja el controlador pausado.

La intención describe los botones mantenidos durante el intervalo aportado.
La equivalencia entre cadencias exige la misma intención por tick: no
reconstruye cambios ocurridos entre muestras HID. No se acumula una lista
ilimitada de eventos. La solicitud pendiente es la última intención vigente,
incluida la liberación de ↑; se actualiza aunque el intervalo no complete
un paso. Durante la mezcla continúan tanto animación como movimiento del
objetivo actual: la parada puede demorarse hasta su salida. Esta limitación
acotada del perfil de inspección queda pendiente de revisar para gameplay.
El giro usa la entrada actual, sin cola.

La pausa/retorno exige soltar controles, incluso botones de cámara futuros.
R con dirección permite inspeccionar un único paso estando pausado; R
durante reproducción consume el comando y no avanza. Reinicio vuelve a la
colocación inicial y espera de HL. No se modifica el visor HL existente.

`platform::ctr::MovementControls` registra y libera el hook APT mediante
RAII. Recibe held/down y el contador ARM11 de la futura entrada de escena;
convierte el delta sin pérdida acumulativa de fracciones de microsegundo.
Un delta mayor de un segundo o un retroceso se entrega como intervalo
inválido; el controlador también rechaza los intervalos >120 ms. Reinicia
la fracción al consumir comandos, durante pausa/guarda y tras hooks que
cambian el estado. HOME/tapa se mapean a suspend/resume y salida APT a quit.
Su conexión al bucle y renderer de habitación corresponde a HM-T4.

Pruebas: replay a cadencias regulares/irregulares con cambios alineados a
tick; reemplazo/cancelación de solicitudes, puente a carrera, mezclas y
parada; límites 39.999/40.000/120.000/120.001 y máximo uint64; fallos en
distintos pasos del lote; pausa/paso/reinicio, HOME/tapa/START, botones
retenidos, hooks duplicados y reentrada. El adaptador se compila contra
dobles SDK y devkitARM; cobertura individual ≥80/80 de ambos módulos.

## Ampliación HG

[HG-T3](heather-turns-native-v1.md) define la selección nativa de cinco
acciones y sus puentes para el perfil 2. [HG-T4.3](../docs/execution/f06-02-heather-turns-integration.md)
implementa esa coordinación: sustituye la intención pendiente basada solo
en movimiento por una acción que distingue ambos giros.
Conserva las garantías de HM, raíz única y contactos, y precisa la política
de intervalos ya corregida en el runtime: recorte a 120 ms hasta un segundo;
por encima, descarte completo. Integración verificada en host con dobles SDK.
[HG-T4.4](../docs/execution/f06-02-heather-turns-resources.md) cierra presupuesto
49,42/64 MiB, inventarios ABI/pila con reserva y compilación ARM `0188790baedd`.
[HG-T5](../docs/execution/f06-02-heather-turns-delivery.md) prepara la entrega
A/B y protocolo; copia a SD verificada y expulsada con respaldo anterior.
La [prueba funcional física de giros](../docs/compatibility/heather-turns-results.md)
queda aceptada según las observaciones del usuario, con límites de lecturas
y sin nuevas medidas de rendimiento/memoria.
Las pruebas adicionales de HM-T5 permanecen aplazadas.

## Secuencia de entrega (actualizada)

- HM-T2b.7a: fijar este alcance, autoridad nativa y exclusiones.
- HM-T3a: contrato y vectores; HM-T3b: planificador puro y gates permanentes.
- HM-T3c completada: puerto de contactos y publicación conjunta con HL; probar fallos
  del resolvedor y ambos canales, errores sin avance parcial y raíz única.
  Respetar transiciones HL existentes: idle→run directo sigue no soportado.
- HM-T3d completada: controles, reloj fijo, pausa/paso/reinicio/suspensión y
  replay del presentador; adaptador 3DS compilado y probado con dobles SDK.
  [Entrega y límites](../docs/execution/f06-01-heather-movement-controls.md).
- HM-T4: escena compartida con límites explícitos de colisión; luego build
  y validación física HM-T5. No hay build nuevo por aprobar solo este contrato.

Pendientes de investigación independiente: aceptación de pared 60, contactos
14/60, variantes de descarte, orden y redondeo general, autoridad exclusiva
de raíz, equivalencia temporal completa. No bloquean este perfil nativo,
pero sí cualquier afirmación de reproducción general del movimiento PS2.
