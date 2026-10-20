# Lifetime guard v1 — LG01–LG08

Como investigador quiero invalidar un intervalo cuando el objeto pueda haberse
liberado o reutilizado, incluso si las capturas posteriores vuelven a mostrar los
mismos bytes. Este contrato define el núcleo host de guardia; la cobertura real
de todos los productores de eventos debe acreditarse antes de aceptar continuidad.

## Requisitos EARS

- **LG01:** WHEN se arma la guardia THEN el núcleo SHALL validar sesión no nula,
  época no nula, contador sin riesgo de desbordamiento, presupuesto acotado y
  rangos físicos alineados, dentro de RAM y sin alias entre estructuras.
- **LG02:** WHEN se recibe una notificación THEN el núcleo SHALL exigir la misma
  sesión y época, contador consecutivo y ciclo no decreciente dentro de 60 segundos;
  SHALL invalidar el intervalo ante huecos, duplicados, retrocesos o presupuesto excedido.
- **LG03:** WHEN una escritura intersecta raíz, cabecera del pool, vtable o campos
  inmutables de la fila THEN el núcleo SHALL invalidar el intervalo antes de la
  escritura, incluso si escribe el mismo valor; SHALL permitir escrituras que
  afecten exclusivamente posición/caché o regiones ajenas a esas estructuras.
- **LG04:** WHEN se notifica reset, intento de restauración, remapeo, cambio de
  configuración, pérdida de eventos, apagado o cancelación THEN el núcleo SHALL
  invalidar permanentemente el intervalo, conservando la primera causa.
- **LG05:** WHEN se sella el intervalo THEN el núcleo SHALL validar la última
  notificación y exigir un ciclo posterior al inicial; IF ya terminó o falló THEN
  SHALL impedir rearmado y cambios posteriores en su resultado.
- **LG06:** WHEN se procesan notificaciones THEN el núcleo SHALL usar almacenamiento
  constante, sin archivos, sockets, emulador, asignación dinámica ni bytes del juego;
  el adaptador SHALL serializar las llamadas antes de cualquier efecto observado.
- **LG07:** WHEN se publica el resultado THEN el investigador SHALL distinguir
  notificaciones suministradas de cobertura acreditada; SHALL mantener deshabilitada
  la aceptación de continuidad de JR mientras falten hooks completos, epoch host,
  binding de extremos, transporte y pruebas de integración.
- **LG08:** WHEN se entrega el núcleo THEN las pruebas SHALL cubrir liberación y
  reciclaje, escrituras iguales, límites de rangos, alias, huecos, restauraciones,
  terminales y presupuestos; SHALL compilar en Debug/Release/sanitizadores y pasar
  los gates de cobertura y regresión, conservando fuentes y evidencia privada.

## Diseño

`sh3::observer::LifetimeGuard` es un núcleo host independiente del lector pausado
OBS1. Recibe datos `LifetimePlan` y `LifetimeNotice` mediante referencias constantes; no conoce PCSX2 ni el
catálogo. El plan contiene sesión, época host, contador y ciclo iniciales, offsets
físicos de raíz/pool/fila/vtable y límite de notificaciones. El resultado conserva
estado, primera causa, último sello aceptado y contadores. No contiene una bandera
que acredite continuidad ni genera `Read`.

Estados: `idle → armed → sealed` o `idle/armed → failed`. Todo terminal es
inmutable; el objeto no se copia ni mueve. Rearmar una guardia activa la invalida.
Para otro intervalo se necesita otra instancia y una nueva identidad de captura.

| Estructura | Bytes protegidos |
|---|---:|
| Raíz del driver | 4 |
| Cabecera del pool | 24 |
| Fila seleccionada | 0–31 y 36–43 |
| Vtable | 12 |

Los campos de posición y caché de la fila pueden cambiar durante seek/read.
El monitor no valida esos valores: JR/CP conservan esa responsabilidad. Toda
escritura que cruce desde un campo permitido a uno protegido se rechaza. El
adaptador debe resolver el destino físico real, incluidos aliases; una dirección
virtual o un PC de función no sustituyen esa resolución. Las cuatro estructuras
completas, incluida la fila de 48 bytes, deben estar separadas físicamente.

El contador u64 numera todas las notificaciones entregadas por el productor,
incluidas escrituras ajenas, checkpoints y cierre. No es el contador regional
OBS1: el núcleo permite como máximo 1.000.000 de notificaciones por intervalo,
con memoria constante. Superar el límite exige abortar, nunca descartar eventos.
Los límites de 48 estados, 256 solicitudes/hits y recursos de LP-D siguen vigentes
para la adquisición; un callback interno sin pausa no crea un estado o breakpoint.

Los ciclos pueden repetirse en operaciones host mientras la CPU está pausada.
El cierre exige progreso respecto al inicio; se usan restas comprobadas para
evitar overflow. La época host debe cambiar **antes** de reset/restauración o
sustitución de VM y no debe formar parte del save state del juego.

## Integración pendiente y criterio de aceptación

Los breakpoints de ejecución del asignador/liberador son referencias para trazar
semántica, no cobertura de todas las escrituras. El productor deberá incluir
intérprete, JIT, escrituras directas/bulk, DMA y modificaciones host, o rechazar
expresamente cualquier modo no cubierto. Debe notificar antes del efecto y
serializar escritores concurrentes. No se debe inferir ausencia de escrituras
porque un callback no llegó.

El observador actual solo adquiere muestras con VM pausada; no alimenta esta
guardia. Un resultado `sealed` acredita únicamente que las notificaciones
suministradas respetaron este contrato. La integración debe armar en el retorno
de apertura y enlazar ese extremo con sus datos observados, incluyendo el hueco
hasta el descriptor finalizado, antes de autorizar continuidad de todo JR.

## Tareas

1. **LG-T1 / LG01,03,04:** contrastar asignación/liberación y las superficies de
   escritura/reset/restore del proveedor fijado. Entregable: matriz de cobertura
   con brechas explícitas, plan privado y dos análisis iguales; sin código original público.
2. **LG-T2 / LG01–06:** implementar núcleo host, intervalos físicos y terminales
   persistentes; fixtures propios de reciclaje, valores iguales, huecos y límites.
3. **LG-T3 / LG08:** añadir suite CTest a CMake host y ejecutar Debug, Release,
   ASan/UBSan, cobertura y regresión. No enlazar el monitor al runtime Nintendo.
4. **LG-T4 / LG07,08:** cerrar trazabilidad y especificar la siguiente unidad de
   integración de productores. Mantener JR cerrado hasta validar cobertura real.
