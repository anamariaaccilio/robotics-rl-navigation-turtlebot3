# Instrucciones de ejecución en terminal — TurtleBot A2C + DAgger

Proyecto: **Fase 1 — Actor-Critic / A2C + DAgger**  
Workspace: `~/turtlebot3_ws`  
Sistema de simulación: **ROS 2 Humble + Gazebo + TurtleBot3 Burger**  
Sistema físico probado: **TurtleBot4 Lite con ROS 2 Jazzy**  

---

# 1. Comandos base

Antes de ejecutar cualquier nodo en la laptop, cargar ROS 2 Humble y el workspace:

```bash
cd ~/turtlebot3_ws
source /opt/ros/humble/setup.bash
source install/setup.bash
export TURTLEBOT3_MODEL=burger
```

Para verificar que el paquete existe:

```bash
ros2 pkg list | grep a2c
ros2 pkg executables turtlebot3_a2c
```

Los ejecutables correctos del paquete son:

```text
turtlebot3_a2c run_a2c
turtlebot3_a2c train_a2c
turtlebot3_a2c run_dagger
turtlebot3_a2c keyboard
```

No usar estos comandos antiguos porque ya no existen en el paquete actual:

```bash
ros2 run turtlebot3_a2c train
ros2 run turtlebot3_a2c dagger
ros2 run turtlebot3_a2c test a2c_sim
ros2 run turtlebot3_a2c test a2c_dagger
```

---

# 2. Ejecución en simulación

## Terminal 1 — Abrir Gazebo

```bash
cd ~/turtlebot3_ws
source /opt/ros/humble/setup.bash
source install/setup.bash
export TURTLEBOT3_MODEL=burger

ros2 launch turtlebot3_gazebo turtlebot3_dqn_stage4.launch.py
```

Esperar a que abra Gazebo y aparezca el TurtleBot3 Burger.

---

## Terminal 2 — Verificar tópicos de simulación

```bash
cd ~/turtlebot3_ws
source /opt/ros/humble/setup.bash
source install/setup.bash
export TURTLEBOT3_MODEL=burger

ros2 topic list | grep -E "scan|odom|cmd"
```

Debe aparecer algo parecido a:

```text
/scan
/odom
/cmd_vel
```

Para verificar que el robot se puede mover manualmente:

```bash
ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.05}, angular: {z: 0.0}}"
```

Para detenerlo:

```bash
ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.0}, angular: {z: 0.0}}"
```

---

# 3. Actor-Critic / A2C en simulación

## Opción A — Ejecutar A2C entrenado

Con Gazebo abierto:

```bash
cd ~/turtlebot3_ws
source /opt/ros/humble/setup.bash
source install/setup.bash
export TURTLEBOT3_MODEL=burger

ros2 run turtlebot3_a2c run_a2c
```

Qué explicar durante la demo:

> Este es el agente Actor-Critic ejecutando una política de acción continua. La red predice velocidad lineal y velocidad angular para navegar hacia la meta evitando obstáculos.

---

## Opción B — Entrenar A2C

Con Gazebo abierto:

```bash
cd ~/turtlebot3_ws
source /opt/ros/humble/setup.bash
source instaall/setup.bash
export TURTLEBOT3_MODEL=burger

ros2 run turtlebot3_a2c train_a2c
```

Qué observar:

```text
Episode / reward / success / collision
L_actor / L_critic / entropy
```

Modelo esperado al finalizar o guardar:

```text
~/turtlebot3_ws/a2c_models/a2c_sim.pth
```

---

# 4. DAgger en simulación

## Terminal 1 — Gazebo

Debe seguir abierto:

```bash
ros2 launch turtlebot3_gazebo turtlebot3_dqn_stage4.launch.py
```

## Terminal 2 — Ejecutar DAgger

```bash
cd ~/turtlebot3_ws
source /opt/ros/humble/setup.bash
source install/setup.bash
export TURTLEBOT3_MODEL=burger

ros2 run turtlebot3_a2c run_dagger
```

Secuencia para la demo:

```text
1. Dejar que A2C pilotee en modo automático.
2. Presionar i para intervenir como experto humano.
3. Usar w, a, s, d para corregir la trayectoria.
4. Presionar t para hacer fine-tuning con los pares capturados.
5. Volver a modo automático y validar la mejora.
6. Presionar q para guardar y salir.
```

Teclas esperadas:

```text
i  -> alternar intervención humana / modo automático
w  -> avanzar
a  -> girar izquierda
d  -> girar derecha
s  -> detener
t  -> fine-tuning con datos DAgger
q  -> guardar y salir
```

Modelo esperado después de DAgger:

```text
~/turtlebot3_ws/a2c_models/a2c_dagger.pth
```

---

# 5. Mostrar modelos guardados

```bash
ls ~/turtlebot3_ws/a2c_models/
```

Debe mostrar, si ya fueron generados:

```text
a2c_sim.pth
a2c_dagger.pth
```

---

# 6. Ejecución en TurtleBot físico

Importante: en físico no se usa Gazebo.  
No ejecutar:

```bash
ros2 launch turtlebot3_gazebo turtlebot3_dqn_stage4.launch.py
```

En físico se usa el bringup del TurtleBot4.

---

## Terminal 1 — Conectarse al TurtleBot físico

Desde la laptop:

```bash
ssh ubuntu@turtlebot4.local
```

Si no funciona por hostname:

```bash
ssh ubuntu@10.42.0.1
```

Dentro del TurtleBot:

```bash
source /opt/ros/jazzy/setup.bash
export ROS_DOMAIN_ID=4
ros2 launch turtlebot4_bringup lite.launch.py
```

Dejar esta terminal abierta.

Nota: si aparece error de `oakd`, corresponde a la cámara OAK-D. Para A2C/DAgger con LiDAR, odometría y velocidad, se puede ignorar inicialmente.

---

## Terminal 2 — Laptop: verificar comunicación con el robot

```bash
source /opt/ros/humble/setup.bash
source ~/turtlebot3_ws/install/setup.bash
export ROS_DOMAIN_ID=4

ros2 topic list | grep -E "scan|odom|cmd"
```

Debe aparecer algo como:

```text
/cmd_audio
/cmd_lightring
/cmd_vel
/cmd_vel_unstamped
/odom
/scan
```

Verificar lectura del LiDAR y odometría:

```bash
ros2 topic echo /scan --once
ros2 topic echo /odom --once
```

Si aparece:

```text
sequence size exceeds remaining buffer
```

es por la mezcla **Humble en laptop** y **Jazzy en robot**. Si los tópicos igual aparecen y `/scan` llega, la comunicación está parcialmente funcionando.

---

# 7. Prueba manual de movimiento físico

Primero probar con `/cmd_vel_unstamped`:

```bash
ros2 topic pub --once /cmd_vel_unstamped geometry_msgs/msg/Twist "{linear: {x: 0.03, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}"
```

Detener:

```bash
ros2 topic pub --once /cmd_vel_unstamped geometry_msgs/msg/Twist "{linear: {x: 0.0, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}"
```

Si no se mueve, revisar el tipo de `/cmd_vel`:

```bash
ros2 topic type /cmd_vel
ros2 topic type /cmd_vel_unstamped
ros2 topic info /cmd_vel
ros2 topic info /cmd_vel_unstamped
```

Si `/cmd_vel` usa `geometry_msgs/msg/TwistStamped`, probar:

```bash
ros2 topic pub --once /cmd_vel geometry_msgs/msg/TwistStamped "{header: {frame_id: 'base_link'}, twist: {linear: {x: 0.03, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}}"
```

Detener:

```bash
ros2 topic pub --once /cmd_vel geometry_msgs/msg/TwistStamped "{header: {frame_id: 'base_link'}, twist: {linear: {x: 0.0, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}}"
```

---

# 8. A2C en físico

Solo ejecutar si la prueba manual de movimiento ya funcionó.

```bash
source /opt/ros/humble/setup.bash
source ~/turtlebot3_ws/install/setup.bash
export ROS_DOMAIN_ID=4

ros2 run turtlebot3_a2c run_a2c --ros-args -r /cmd_vel:=/cmd_vel_unstamped
```

---

# 9. DAgger en físico

Solo ejecutar si la prueba manual y A2C físico ya funcionaron.

```bash
source /opt/ros/humble/setup.bash
source ~/turtlebot3_ws/install/setup.bash
export ROS_DOMAIN_ID=4

ros2 run turtlebot3_a2c run_dagger --ros-args -r /cmd_vel:=/cmd_vel_unstamped
```

---

# 10. Comando de emergencia

Tener siempre una terminal lista para detener el robot.

Si se usa `/cmd_vel_unstamped`:

```bash
source /opt/ros/humble/setup.bash
export ROS_DOMAIN_ID=4

ros2 topic pub --once /cmd_vel_unstamped geometry_msgs/msg/Twist "{linear: {x: 0.0, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}"
```

Si se usa `/cmd_vel` con `TwistStamped`:

```bash
source /opt/ros/humble/setup.bash
export ROS_DOMAIN_ID=4

ros2 topic pub --once /cmd_vel geometry_msgs/msg/TwistStamped "{header: {frame_id: 'base_link'}, twist: {linear: {x: 0.0, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}}"
```

---

# 11. Problemas frecuentes

## Error: `No executable found`

Causa: se está usando un nombre antiguo de ejecutable.

Incorrecto:

```bash
ros2 run turtlebot3_a2c train
ros2 run turtlebot3_a2c dagger
ros2 run turtlebot3_a2c test a2c_sim
```

Correcto:

```bash
ros2 run turtlebot3_a2c train_a2c
ros2 run turtlebot3_a2c run_dagger
ros2 run turtlebot3_a2c run_a2c
```

---

## Error: `/reset_simulation no disponible`

En simulación puede salir si Gazebo no está abierto o no terminó de cargar.

Solución:

```bash
ros2 service list | grep reset
```

Si no aparece `/reset_simulation`, reiniciar Gazebo y esperar a que cargue.

En físico es normal que no exista `/reset_simulation`. En ese caso, el código debe permitir modo físico sin reset automático.

---

## Mensaje: `sequence size exceeds remaining buffer`

Aparece al comunicar laptop ROS 2 Humble con TurtleBot4 ROS 2 Jazzy. No necesariamente bloquea todo, pero indica incompatibilidad o advertencia de serialización DDS.

Si afecta demasiado, la solución más estable es correr el cliente físico desde un entorno con:

```text
Ubuntu 24.04 + ROS 2 Jazzy
```

---

## Mensaje: `Waiting for at least 1 matching subscription(s)...`

Significa que se está publicando en un tópico sin ningún suscriptor.

Revisar:

```bash
export ROS_DOMAIN_ID=4
ros2 topic info /cmd_vel
ros2 topic info /cmd_vel_unstamped
```

Usar el tópico que tenga `Subscription count: 1`.

---

# 12. Resumen rápido de demo

## Simulación

Terminal 1:

```bash
cd ~/turtlebot3_ws
source /opt/ros/humble/setup.bash
source install/setup.bash
export TURTLEBOT3_MODEL=burger
ros2 launch turtlebot3_gazebo turtlebot3_dqn_stage4.launch.py
```

Terminal 2 — A2C:

```bash
cd ~/turtlebot3_ws
source /opt/ros/humble/setup.bash
source install/setup.bash
ros2 run turtlebot3_a2c run_a2c
```

Terminal 2 — DAgger:

```bash
cd ~/turtlebot3_ws
source /opt/ros/humble/setup.bash
source install/setup.bash
ros2 run turtlebot3_a2c run_dagger
```

## Físico

Robot:

```bash
source /opt/ros/jazzy/setup.bash
export ROS_DOMAIN_ID=4
ros2 launch turtlebot4_bringup lite.launch.py
```

Laptop:

```bash
source /opt/ros/humble/setup.bash
source ~/turtlebot3_ws/install/setup.bash
export ROS_DOMAIN_ID=4
ros2 run turtlebot3_a2c run_a2c --ros-args -r /cmd_vel:=/cmd_vel_unstamped
```
