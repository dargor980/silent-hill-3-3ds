# Procedencia candidata de punteros MIPS v1

F02.07/camera-pointer-origin-eu; RF02.02/.07/.08, RNF06.01/.04/.07,
RNF07.06-.09 y RNF11.05-.09. Investigación estática parcial, no decompilador.

## Requisitos EARS

- **CP01:** WHEN inicia el seguimiento THEN SHALL fijar hashes de ISO, perfil,
  sondeo de cámara e informe de consumidor; SHALL regenerar el último desde la
  ISO verificada y exigir igualdad canónica completa antes de usar sus sitios.
- **CP02:** WHEN busca referencias THEN SHALL recorrer solo segmentos ejecutables
  respaldados del mapa ELF, en lecturas <=4096 y <=16 MiB. SHALL reconocer destinos
  directos mediante PC+4 y desplazamiento signado o región de salto; SHALL validar
  su mapeo y conservar como sintácticas las referencias. Un destino sin bytes respaldados SHALL contabilizarse sin crear arista seleccionada. PF_X no prueba código.
- **CP03:** WHEN construye un grafo local THEN SHALL limitarlo a <=16 sitios,
  <=4096 bytes por ventana (desde 512 bytes antes del destino hacia atrás hasta el
  final del patrón), <=4096 referencias seleccionadas y <=2048 aristas por ventana.
  No declarar límites de función ni accesibilidad por proximidad. Referencias desde
  fuera de la ventana SHALL producir una raíz desconocida, no una entrada confirmada.
- **CP04:** WHEN modela un salto soportado THEN SHALL mantener el delay slot en un
  contexto separado; ramas normales ejecutan el slot en ambas salidas y ramas
  likely solo en la tomada. J/JR no tienen continuación local; JAL/JALR retornan
  hipotéticamente a PC+8, con invalidación de todos los GPR no cero tras la llamada.
  Una transferencia en delay slot SHALL cortar ese camino como no soportado.
- **CP05:** WHEN rastrea el registro base antes del avance del patrón THEN SHALL
  recorrer predecesores y propagar copias y ajustes soportados; cargas, constantes,
  escrituras no interpretadas, llamadas, fronteras y raíces externas SHALL producir
  terminales distintos. Un ajuste se registra sin afirmar el valor resultante.
  Instrucciones desconocidas SHALL invalidar la procedencia; su posible continuación
  lineal es solo una hipótesis, nunca una arista probada. No asumir convenio de registros.
- **CP06:** WHEN hay convergencia o ciclos THEN SHALL deduplicar estados y conservar
  la limitación `revisited_state`; SHALL detener a <=2048 estados y profundidad 512,
  registrando presupuesto agotado como desconocido explícito. No atribuir una carga
  anterior al sitio a través de una llamada o sobrescritura desconocida.
- **CP07:** WHEN emite resultados THEN SHALL guardar solo metadatos privados:
  posiciones/hash de ventanas, referencias, conteos y categorías de procedencia.
  No volcar instrucciones, bytes, textos ni constantes originales. Todos los sitios
  SHALL mantener vínculo de recurso y accesibilidad sin probar, capacidades vacías
  y F02.07 pendiente. Sin vínculo demostrado no interpretar colas ni campos 92/108.
- **CP08:** IF identidad, I/O, mapeo obligatorio de ventana o presupuesto estructural falla THEN SHALL
  abortar sin publicar resultado parcial; publicar exclusivamente después del cierre
  estable. WHEN verifica THEN SHALL usar fixtures propios de delay slots, llamadas,
  ramas convergentes, indirectos, sobrescrituras y límites; comparar dos sondeos
  reales y ejecutar quality/cobertura sin originales en CI.

## Diseño y ejecución

`mips_flow` interpreta un subconjunto de efectos GPR/control y rechaza inferencias
fuera de él. `pointer_graph` reúne referencias y el grafo, y hace seguimiento por
un puerto de lectura; `camera_pointer` reconcilia evidencia y compone ISO/publicación.
El seguimiento interprocedural tiene profundidad cero: las llamadas son fronteras,
no se simula su retorno ni el estado de registros del programa real.

Orden: contrato → efectos/control y fixtures → referencias/grafo/procedencia → CLI
e identidad → doble contraste → calidad e informe. Siguiente experimento se elige
por las fronteras observadas, sin promover el patrón previo a consumidor confirmado.

Fuente primaria de codificaciones/PC relativo: MIPS/binutils
`9decc44bc67d9fb4248c2afe4fde77174e8abf80`, ya fijado en
[procedencia](../docs/compatibility/camera-consumer-research-evidence.json).
No se adopta ni ejecuta código de ese proyecto; implementación propia, sin librería nueva.
