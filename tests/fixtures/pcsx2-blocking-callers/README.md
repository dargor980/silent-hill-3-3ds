# Dependencias del callback — SRC86

El soporte propio reutiliza los 71 fragmentos privados fijados en SRC85.
No modifica PCSX2 ni simula una sesión de RetroAchievements. QtCore, QThread,
VU/GS y Mach conservan el alcance real/doble documentado en SRC85.

Dos casos, free y contended, ejecutan una llamada UI→CPU síncrona después de
retener ambos workers. El aviso cancela antes del callback y este comprueba
retiro VU/GS/PINE, conservación de payload y entrega única.

En contended, un tercer hilo posee un std::mutex real. El callback comprueba que
no puede adquirirlo y anuncia su llegada. El dueño verifica que el observador ya
se retiró mientras CPU/UI todavía no han terminado; solo entonces libera su
propio mutex. CPU completa y UI retorna, con el anuncio vivo hasta ese retorno.
En free, el callback adquiere el recurso sin contención. Ambos permiten otro
intento después de terminar.

La prueba no desbloquea desde otro hilo un mutex ajeno ni necesita un timeout
para aprobar. El supervisor limita procesos colgados a 15 s. Los dos casos
pasan en normal, ASan/UBSan y QtCore TSan. Demuestran una dependencia controlada,
no que Logout o un backend de dispositivos real esté libre de deadlocks.
