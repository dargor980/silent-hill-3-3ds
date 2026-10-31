# Heather: comparación de skinning CPU/GPU

Instancia preparatoria **HS de F06.03**, iniciada el 2026-10-30 tras la
[aceptación funcional de HG](../../compatibility/heather-turns-results.md).
Se limita a Heather, sus cinco clips y hp34 de `0188790baedd`.
F06.02 global y G04/G05 siguen abiertos; el perfil de inspección permite
comparar esta carga sin declarar un límite general del juego.
HM-T5 adicional y la investigación de pared 60 permanecen aplazadas.

## Requisitos de la comparación

- **HS01 — Identidad.** WHEN se compare una alternativa THEN SHALL usar
  las mismas entradas A/B autenticadas, poses, instancia, cámara, geometría,
  UV, texturas, materiales y visibilidad que el baseline. SHALL registrar
  fuentes, compilador, opciones, shader y build. Ningún recurso original
  entra en git ni CI; las pruebas públicas usan datos inventados.
- **HS02 — Deformación.** WHEN se evalúe un vértice THEN SHALL conservar
  las 1–3 influencias activas y su orden, posición Q4 y pesos/UV Q12.
  La matriz primaria es la pose del hueso; cada auxiliar es
  `pose[target] * helper`, con identidad propia aunque comparta target.
  SHALL calcular `p = Σ (weight[j]/4096) * matrix[j] * (position/16, 1)`
  en cuatro componentes, sin normalizar pesos ni forzar W=1.
  SHALL aplicar la instancia una sola vez y conservar `room_position`:
  resta del origen multiplicada por W, escala y signos X/−Y/−Z.
  El skinning no puede modificar reloj, movimiento, contactos o animación.
- **HS03 — Orden y transparencia.** WHEN se emitan opacos THEN SHALL
  conservar materiales y triángulos en orden, dividiendo solo en fronteras
  de triángulo. WHEN se emita cabello/vidrio THEN SHALL conservar la
  ordenación global CPU por profundidad descendente, material y primer
  índice. SHALL conservar estados de mezcla/profundidad, alpha, winding,
  texturas y salidas completas del shader. Una agrupación de paletas del
  orden original de cabello no acredita un plan transparente válido.
- **HS04 — Recursos y fallos.** WHEN se prepare un candidato THEN SHALL
  reservar buffers fuera del cuadro, validar índices/pesos/capacidades y
  rechazarlo sin publicar planes parciales. WHEN se dibuje THEN SHALL
  esperar propiedad GPU antes de escribir buffers compartidos y conservar
  recuperación/pausa/R/reinicio/HOME/tapa. SHALL medir pico coexistente,
  staging, pila, asignaciones y liberación; incluir la reserva del SDK.
- **HS05 — Medición.** WHEN se mida THEN SHALL distinguir simulación y
  contactos, animación/pose, paleta, deformación CPU, ordenación/expansión,
  espera de propiedad, copia/flush y envío, GPU y cadencia de presentación.
  SHALL identificar el cuadro de cada dato GPU y no sumar intervalos
  solapados ni `GPU previous` a CPU. Carga/descompresión y audio deberán
  figurar por separado, o como no aplicables si no se ejecutan.
- **HS06 — Decisión.** WHEN se proponga un límite o mejora THEN SHALL
  aportar curva de coste y medición en la consola identificada, además de
  equivalencia numérica, visual, memoria y regresiones. Un conteo de
  matrices, benchmark host, doble SDK o compilación ARM no prueba capacidad
  ni velocidad de la GPU. Las capacidades del análisis son parámetros;
  los registros disponibles se verificarán contra shader/SDK fijados antes
  de implementar el candidato.

Aplican RNF02.07, RNF01.05 y los gates de código RNF07.06–09/RNF11.05–09.

## Alternativas y unidades

| Alternativa | Trabajo previsto | Estado |
| --- | --- | --- |
| CPU actual | Deformar todos los vértices, ordenar y expandir índices | Baseline funcional `0188790baedd` |
| Híbrida | Opacos en GPU; cabello y ordenación con vidrio en CPU | Candidata para primer prototipo |
| GPU con profundidad CPU | Deformación GPU también del cabello; conservar posiciones CPU para ordenar | Comparación posterior si aporta beneficio medible |

Las dos alternativas GPU conservan el recorrido de escena completo. No se
asume que mover la deformación elimine el coste de ordenación o envío.
La candidata híbrida se prioriza por la separación observada de vértices;
**todavía no es una elección de implementación final**.

- [x] **HS-T1 — Inventario y contrato de comparación.** Autenticar A/B;
  cotejar SRI2 con el lector C++; medir influencias, matrices, W, materiales,
  vértices compartidos y particiones opacas sin reordenar; cubrir límites y
  fallos con datos sintéticos. [Resultado](../../benchmarks/skinning.md).
- [x] **HS-T2 — Contrato de paletas y vectores del prototipo.** Verificar
  registros/atributos/instrucciones en el SDK fijado; elegir representación
  y capacidad efectiva. Congelar vectores para 1/2/3 influencias, W
  deficiente, helpers con el mismo target, límites de lote, transformaciones
  y clips/transiciones HG. Fijar tolerancias numéricas y de proyección antes
  de evaluar resultados GPU; conservar CPU transparente exacta.
  [HSN v1](../../../schemas/heather-skinning-native-v1.md) y
  [ejecución](../../execution/f06-03-heather-skinning-contract.md): 30 matrices,
  54 casos numéricos, 16 comprobaciones SDK y ABI ARM; sin ejecución GPU.
- [x] **HS-T3 — Prototipos y ensayo host.** Implementar CPU de referencia
  y candidato híbrido acotado, con selección explícita y fallback de carga;
  validar vectores, orden, fallos, memoria/pila y regresiones HL/HM/HG.
  Instrumentar intervalos disjuntos y verificar que no se pierdan muestras.
  [Ejecución host](../../execution/f06-03-heather-skinning-prototype.md):
  54 vectores, A/B nativo, fallback, transparencia exacta, cero asignaciones
  por cuadro, 49,89 MiB de presupuesto y pila dentro de 32 KiB. Sin ejecución GPU.
- [x] **HS-T4 — ARM y paquete comparativo.** Compilar shaders/ejecutables,
  verificar ABI/presupuesto, preparar A/B y protocolo específico HS.
  Conservar el paquete HG aceptado para volver al baseline.
  [Ejecución](../../execution/f06-03-heather-skinning-delivery.md): selector,
  ARM `f64760613473`, 49,94 MiB incluyendo captura y staging, A/B verificados y
  [protocolo](../../compatibility/heather-skinning.md). SD sin modificar;
  GPU física y perfiles de carga creciente pendientes.
- [ ] **HS-T5 — Medición física y decisión.** En una sesión autorizada,
  comparar CPU/candidato con el mismo recorrido y condiciones; al menos
  tres ventanas alternadas por variante tras calentamiento, con tamaños de
  muestra, mediana/p95/máximo y cuadros fallidos. Incluir cargas crecientes
  de huesos/influencias/lotes sin sustituir el caso real. Registrar curva,
  límites y decisión; mantener CPU si la alternativa no acredita ventaja.

HS-T5 será un ensayo propio; no reactiva las pruebas aplazadas de HM-T5.
El perfil HS completo tampoco cierra automáticamente F06.03 para otros
personajes, escenas o hardware.
