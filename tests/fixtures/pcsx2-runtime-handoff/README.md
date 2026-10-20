# Fixture propia RH

Extiende la fixture RC con el adaptador frontend propio, puerto CPU, deadline
absoluto, confirmación de retirada y trabajador/entrega DW. El despacho Host se
sustituye por una cola local que conserva el callback y comprueba block=false.
IO ejecuta en un hilo distinto a CPU; VU/GS y DW son hilos reales. Se verifican
callbacks duplicados/tardíos, cancelación antes de la cola, rechazo VM, excepción
de despacho, ausencia de callback, retorno con frame sintético y trabajo bloqueado.

Los cuerpos privados y los 17 prefijos conservan las limitaciones de RC: VM,
Qt, PINE y colas son dobles. No representa un frontend Qt enlazado, un socket
nativo autenticado, inventario nativo dentro de VM ni ejecución del juego.
