# Prueba física — SH3 animation inspection

Estado: **AI-T5 aprobada por confirmación del usuario el 2026-10-20**, New 2DS XL y
Homebrew Launcher. Build **`a1629eeace22`**. La
[ejecución](../execution/f03-02-animation-inspection.md) distingue host, ARM y Azahar.

Extraer `f03-02-3ds-animation-v2/sd-card.zip` en la raíz de la SD. Deben quedar
`animation.san`, `.3dsx`, `.smdh` y `LEEME.txt` dentro de
`/3ds/sh3_animation_probe/`. Conservar los demás visores y expulsar la SD
de forma segura. No se necesita CIA/FBI.

**Entrega copiada a la SD «NO NAME»** el 2026-10-20, build `a1629eeace22`:
cuatro archivos, 225.678 bytes, en `/3ds/sh3_animation_probe/`. Tamaños y
SHA-256 comprobados mediante lectura posterior de la SD. Se conservaron los
otros visores y se retiraron únicamente los auxiliares `._` de esta copia.
La SD se expulsó correctamente con `diskutil eject`.
Comprobante privado: `f03-02-animation-native-check-v1/sd-copy.json`, SHA-256
`279dcafa09b869e3ad76eb4ca9bd2109b004e57de2f21cae505e74d80106393c`.
Confirmación posterior del usuario: «Lo probé en la 2DS XL: se ven los ejes
animados y funcionan A, R, L, la cámara, START, tapa y HOME».

| Comprobación física | Resultado comunicado |
|---|---|
| Ejes y movimiento | Correctos |
| A, R y L | Funcionan |
| Cámara | Funciona |
| START | Funciona |
| Tapa y HOME | Funcionan |

Se vincula la prueba al build entregado `a1629eeace22`; el usuario no transcribió
el identificador mostrado. La duración, FPS, cada valor Q12 y la equivalencia
visual con PS2 no se midieron físicamente. Los pasos siguientes se conservan
como protocolo de repetición, sin atribuir al usuario mediciones no comunicadas.

1. Abrir **SH3 animation inspection** y comprobar build `a1629eeace22`.
2. Ver tres juegos de ejes: rojo X, verde Y, azul Z. Uno queda separado y
   los otros dos tienen un enlace gris. El movimiento es sutil: observar
   los ejes enlazados durante varias vueltas. No debe aparecer la malla del caballo.
3. A debe congelar movimiento y contador. L debe llevarlo a cero conservando
   la pausa. Cada pulsación independiente de R debe sumar 3686 módulo 98304.
   A vuelve a reproducir; R no debe forzar pasos durante reproducción.
4. Cruceta cambia la cámara, X/Y acerca/aleja y B restaura el encuadre. Estos
   controles también deben funcionar con la animación pausada.
5. Probar tapa y HOME tanto reproduciendo como en pausa; al volver, soltar
   los controles. Debe conservarse la pausa sin recuperar de golpe el tiempo
   transcurrido fuera de la aplicación.
6. START debe volver al Homebrew Launcher, también tras reanudar.

En futuras repeticiones, registrar build, controles, movimiento, duración y errores.
Daño `0x144A`, muerte `0x144B`, malla y skinning quedan pendientes
de investigación/implementación y no forman parte del éxito de esta prueba.
