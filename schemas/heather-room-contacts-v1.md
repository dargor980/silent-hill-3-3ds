# HRC v1 — Contrato numérico de contactos de habitación

2026-10-29. **HM-T4b.1: contrato y vectores**, previo al núcleo C++ de
HM-T4b.2. Refina [HR04–08/10–11](heather-room-profile-v1.md) y el puerto
[HMN08–12](heather-movement-native-v1.md). Perfil
`static-xz-aabb-stop-v1`; no describe el solver PS2.

**Implementación:** [HM-T4b.2 completada](../docs/execution/f06-01-heather-room-contacts.md).
**Preparación:** [HM-T4b.3 completada](../docs/execution/f06-01-heather-room-preparation.md),
con [paquetes privados A/B](heather-room-contacts-package-v1.md) y cotejo del
recorrido con oráculo independiente. La integración gráfica sigue en HM-T4c.
El contrato fijado se conserva; preparación de recursos privados e integración
de escena siguen pendientes.

## Requisitos EARS

- **HRC01** WHEN prepara contactos THEN el preparador SHALL validar perfil,
  capacidad, memoria y geometría completa antes de publicar una escena
  inmutable. IF falla THEN SHALL conservar la escena anterior íntegra.
- **HRC02** WHEN evalúa geometría THEN el núcleo SHALL interpretar los bits
  binary32 como números racionales exactos, incluidos subnormales; SHALL
  expandir cajas y erosionar suelo sin redondear sus fronteras.
- **HRC03** WHEN resuelve una consulta THEN SHALL validar ambos XYZ y el
  estado inicial antes del barrido cerrado continuo. IF el origen toca una
  barrera o el borde del suelo THEN SHALL devolver `invalid_start`.
- **HRC04** IF un segmento válido toca una caja o alcanza el borde del suelo
  THEN SHALL copiar todo `from`; ELSE SHALL copiar todo `requested`.
  SHALL NOT usar epsilon, avance parcial, deslizamiento ni la guarda como
  tolerancia de penetración.
- **HRC05** IF falla la consulta THEN SHALL conservar todos los bytes de
  salida. WHEN tiene éxito THEN SHALL copiar los bits XYZ del extremo elegido,
  incluidos ceros con signo, sin recalcular ni transformar su posición.
- **HRC06** WHILE consulta THEN SHALL usar memoria acotada, sin heap, I/O,
  SDK, callbacks ni estado mutable de gameplay; SHALL ignorar el ordinal
  para decidir el contacto y permitir repetir la misma consulta.
- **HRC07** WHEN acepta la implementación THEN las pruebas SHALL exigir
  identidad de clasificación y bits de salida frente a los vectores propios,
  contraste geométrico independiente y gates por módulo ≥80/80; SHALL
  distinguir contrato verificado, ejecución host, compilación ARM y consola.

Trazabilidad: HRC01/06 → HR05/07/10; HRC02–05 → HR04/06–08;
HRC07 → HR11. Los contratos HMN de animación y transacción siguen vigentes.

## Entradas y alcance

La escena preparada conserva **coordenadas mundiales binary32 originales**:
suelo rectangular X/Z, `floor_y`, cajas bloqueadoras X/Z y origen de escena
como metadato. Cada caja usa `[xmin,xmax,zmin,zmax]`. El preparador HM-T4b.3
debe comprobar que el suelo fuente realmente es un rectángulo horizontal;
su AABB no autoriza sustituir un polígono de suelo arbitrario.

Todos los componentes de geometría, origen y consulta son finitos y están
en `[-1000000,1000000]`, inclusivo, como HMN. El límite se comprueba sobre
las entradas; una frontera expandida puede excederlo. Las cajas permiten
`min=max` en uno o ambos ejes. No se invierten ni ordenan límites defectuosos.
La altura del suelo es finita/acotada; el perfil hp34 exige Y=0.

Semiextensión **175**, guarda **1**, suma exacta **R=176**, constantes de
este perfil. No se admite radio configurable en el runtime v1. Fixtures de
0–32 cajas ejercitan el núcleo; el preparador de hp34 debe exigir exactamente
32 y los 34 registros/procedencias de HR05, incluido el techo excluido.
Una escena sintética vacía no permite aceptar un recurso hp34 incompleto.

`MovementContactQuery` mantiene `from`, `requested` y ordinal uint32.
Se aceptan todos los ordinales, incluidos 0 y `UINT32_MAX`; no se incrementan
ni interpretan como tiempo. No se limita la longitud del segmento a 28/70:
el barrido debe detectar también un cruce largo con extremos libres.
Ambos Y deben ser numéricamente iguales a `floor_y`; +0 y −0 son iguales
en predicados. No se ajusta Y ni se permite movimiento vertical.

El origen **no se suma ni resta** para estos predicados. CLD ya está en
mundo. Tampoco intervienen yaw, escala 0,002, base de render, pose o raíz.
Trasladar una fixture exige trasladar geometría y extremos con valores
binary32 representables; cambiar solo el metadato de origen no mueve nada.

## Aritmética exacta y límite de almacenamiento

No basta con calcular cocientes en double: una división puede redondear una
separación a tangencia, y sumar 176 puede borrar un subnormal. La guarda
es una ampliación geométrica exacta, no una solución a esos redondeos.
La decisión v1 es usar **predicados exactos con enteros de tamaño fijo**.
No hay división flotante, tolerancia, cuantización ni zona indeterminada.

Todo binary32 finito es un múltiplo de `u=2^-149`. Sea `I(v)=v/u`:

- Campos de bits: signo `s`, exponente almacenado `e`, fracción `m`.
- Si `e=0`: magnitud entera `m` (incluye ambos ceros).
- Si `1≤e≤254`: magnitud `(2^23+m) << (e-1)`.
- Aplicar signo; normalizar el cero solo para comparar. `e=255` se rechaza
  **antes de operar**, incluso NaN señalizante; no depender de FTZ/DAZ.
- Validar el límite antes de construir el entero. `I(R)=176 << 149`.

Con las entradas acotadas, `|I(v)|<2^169`. Incluso tras ±R,
`1000000+176<2^20`; las diferencias entre frontera y extremo o entre extremos
tienen magnitud `<2^170`. Por tanto, **192 bits de magnitud más signo**
bastan para coordenadas/diferencias. Comparar razones exige productos
de magnitud `<2^340`: **352 bits de magnitud más signo** bastan. No hay que
restar dos productos: comparar signo/magnitud evita otro bit de acarreo.

Representación viable para HM-T4b.2: seis limbs uint32 para magnitudes y
once para productos, con operaciones/carries sin overflow firmado. No
requiere `__int128`, enteros de tamaño dinámico ni biblioteca multiprecisión.
Una alternativa solo será admisible si demuestra los mismos predicados
exactos para todo el dominio, no solo coincidencia en muestras.

Conservar cajas fuente como binary32 (32×16=512 bytes) y convertir **una
caja por vez**; almacenar todas las cajas como enteros anchos malgasta el
presupuesto. Límite conjunto, inclusivo: **4096 bytes** para almacenamiento
residente de contactos más máximo scratch simultáneo. Incluye adaptador,
padding, copias provisionales de preparación y pila/scratch de helpers;
no incluye los buffers fuente del preparador host ni el coordinador HMN.
No se permiten buffers estáticos ocultos ni heap por consulta. HM-T4b.2
aporta layout y cota de pila incluidas llamadas: reserva residente 576 bytes
y scratch 2560, total 3136. La [evidencia](../docs/execution/f06-01-heather-room-contacts.md)
separa host, ARM y rutinas externas. El producto se almacena completo en
12 limbs (el último siempre cero), sin cambiar la cota matemática de 340 bits.
El rendimiento físico aún no está medido.

## Barrido normativo

Todas las operaciones siguientes son racionales exactas sobre esas entradas.
Suelo transitable abierto:

```text
F = (floor.xmin+R, floor.xmax-R) × (floor.zmin+R, floor.zmax-R)
B[i] = [box.xmin-R, box.xmax+R] × [box.zmin-R, box.zmax+R]
```

Si F es vacío en cualquier eje, la escena es inválida. Un `from` válido
está estrictamente dentro de F y fuera de todas las B[i], incluida su
frontera. Validar `from` aunque la consulta sea nula o el destino esté libre.

1. Si `requested` no está estrictamente dentro de F, bloquear. F es convexo:
   cuando ambos extremos están dentro, todo el segmento permanece dentro.
2. Para cada B[i], empezar intervalo paramétrico cerrado `[lo,hi]=[0,1]`.
   En cada eje, `d=requested-from`.
3. Si `d=0`, el eje no restringe el intervalo cuando `min≤from≤max`;
   si `from` está fuera, esa caja no se toca. Nunca dividir por cero.
4. Si `d≠0`, formar las razones `(min-from)/d`, `(max-from)/d`, normalizar
   denominadores positivos y ordenar. Intersectar con `[lo,hi]`.
   Comparar `n1/d1` con `n2/d2` mediante `n1*d2` y `n2*d1`, exactos.
5. `lo>hi` significa separación; **`lo=hi` es contacto**. Si queda intervalo
   después de ambos ejes, bloquear. Si ninguna caja se toca, aceptar destino.

La consulta nula válida copia `requested`; una consulta nula en frontera
es `invalid_start`. Cajas fuente degeneradas son válidas y se expanden con
R exactamente igual que las demás. El orden de cajas, duplicados y el
sentido de un segmento con ambos extremos válidos no cambian la decisión.
No se publica normal, tiempo de impacto ni identificador de primera pared.

## Errores, prioridad y publicación

Nombres de resultado del núcleo; no amplían el enum del puerto.
Preparación valida en este orden y devuelve el primer error:

| Resultado | Condición |
| --- | --- |
| `unsupported_profile` | ID distinto o parámetros 175/1 distintos. |
| `capacity_exceeded` | Más de 32 bloqueadores. No leer un bloqueador fuera de capacidad. |
| `budget_exceeded` | Residente + máximo scratch simultáneo >4096 bytes. Sumar sin overflow. |
| `invalid_geometry` | No finito, fuera de límites, caja/suelo invertidos. Revisar todo antes de publicar. |
| `empty_floor` | Suelo erosionado sin interior estricto en al menos un eje. |
| `ok` | Publicar solo cuando todas las comprobaciones han pasado. |

La falta de recurso/disponibilidad es una escena no preparada; no es una
escena con cero cajas. Un fallo de preparación conserva la anterior si
existía. La API de publicación debe impedir consultar una escena parcial.
Fuentes, cantidades/listas o clases CLD discordantes fallan en HM-T4b.3
antes de esta preparación; no se sustituyen por cajas vacías.

Consulta de una escena preparada, en este orden:

| Resultado del núcleo | Puerto | Escritura XYZ |
| --- | --- | --- |
| `unavailable` (sin escena) | `unavailable` | Ninguna. |
| `invalid_query` (cualquier XYZ no finito) | `unsupported` | Ninguna. |
| `out_of_bounds` (cualquier XYZ fuera de ±1000000) | `unsupported` | Ninguna. |
| `off_floor` (cualquier Y distinta del suelo) | `unsupported` | Ninguna. |
| `invalid_start` (from fuera de F o dentro/sobre una B) | `unsupported` | Ninguna. |
| `ok`, libre | `accepted` | Copiar bits XYZ completos de `requested`. |
| `ok`, bloqueado | `accepted` | Copiar bits XYZ completos de `from`. |

El bloqueo es éxito: giro, ordinal y animación siguen la transacción HMN.
Un error conserva la instantánea del actor y pausa según HM-T3d. No hay
despenetración implícita. Incluso si `from` ya está penetrado, un Y de
destino inválido devuelve `off_floor` por prioridad.

Staging local antes de escribir permite que la salida aliase `from` o
`requested`; los errores no modifican ningún byte, incluido padding si el
tipo lo tiene. El contrato es transaccional en un hilo; no sincroniza hilos.
No guardar «último contacto» en el resolvedor ni consumir el ordinal.

## Vectores y oráculo independientes

[Fixture versionada](../tests/fixtures/synthetic/heather-room-contacts-v1.json)
con geometría inventada, expectativas literales y etiquetas estables. Los
escalars son enteros exactamente representables o cadenas `f32:XXXXXXXX`
de ocho dígitos hexadecimales (bits, sin endian implícito). NaN/Inf solo se
usan como entradas negativas. No se permite NaN JSON ni redondeo decimal
implícito. XYZ de salida se compara por bits; tolerancia **cero**.

La caja base `[0,100,-100,100]` se expande a
`[-176,276,-276,276]`; el suelo `[-1000,1000,-1000,1000]` se erosiona a
`(-824,824)×(-824,824)`. Por ejemplo:

| Segmento X/Z | Resultado |
| --- | --- |
| (−500,0) → (−200,0) | Libre; copiar destino. |
| (−500,0) → (500,0) | Bloqueado aunque ambos extremos estén libres. |
| (−500,276) → (500,276) | Tangencia; bloquear. |
| (−500,48) → (48,−500) | Esquina única en t=81/137; bloquear. |
| (−500,0) → (−176,0) | Contacto en t=1; bloquear. |
| (−176,0) → (−500,0) | Error de estado inicial. |

El [oráculo de prueba](../tests/python/helpers/heather_room_contact_oracle.py)
usa `Fraction` y orientación/intersección contra los **cuatro lados** del
rectángulo, no el algoritmo de intervalos ni los limbs previstos. No importa
código de producción ni lee recursos privados. Las
[pruebas de contrato](../tests/python/test_heather_room_contacts_contract.py)
contrastan los literales, reglas de prioridad, relaciones geométricas y la
cota de enteros. El oráculo no es una implementación runtime.

Las fixtures cubren libre, recto, oblicuo, esquina, tangencia, cruce continuo,
cajas fuente línea/punto, estado nulo, paralelas, frontera ±1 ULP, guarda,
origen grande, valores extremos, ceros con signo, subnormales, Y/NaN/Inf,
memoria y capacidad inclusivas/excedidas, prioridad y escena indisponible.
El valor `copy_from` de cada expectativa es `from`, `requested` o `null`;
`null` exige salida intacta. Los bytes centinela están fijados en el JSON.

HM-T4b.2 alimenta **estos mismos bits** al núcleo/puerto y comprueba centinela,
ambos alias, repetición y escena intacta tras fallos. También pasan 768
consultas generadas adicionales, cobertura individual y compilación ARM.
HM-T4b.3 debe cotejar las 32 cajas y cinco tramos privados A/B con el oráculo,
sin publicar sus coordenadas. Integración y aceptación física siguen pendientes.
