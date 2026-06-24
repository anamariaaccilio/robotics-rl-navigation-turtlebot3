# Configuración y prueba en TurtleBot3 físico

Este documento resume los pasos para pasar del entorno de simulación en Gazebo al TurtleBot3 físico.

La idea principal es:

```text
En simulación:
Gazebo + agente DQN/A2C

En robot físico:
TurtleBot3 real + sensores reales + modelo entrenado + publicación en /cmd_vel
```

> Importante: en el robot físico primero se recomienda **probar inferencia**, no entrenar desde cero. El entrenamiento se hace en simulación y luego se carga el modelo entrenado en el robot/laptop.

---

## 1. Supuestos del entorno

Se asume que ya tienes en tu laptop:

```text
Ubuntu 22.04
ROS 2 Humble
Workspace: ~/turtlebot3_ws
Modelo: TurtleBot3 Burger
Paquete DQN funcionando en Gazebo
Paquete Actor-Critic compilado en Gazebo
```

También se asume que el TurtleBot3 físico tiene:

```text
Raspberry Pi / SBC configurada
OpenCR conectado
LDS activo
WiFi configurado
ROS 2 instalado
Paquete turtlebot3_bringup disponible
```

---

## 2. Variables que deben coincidir

En la laptop y en la Raspberry Pi del robot, usar el mismo modelo:

```bash
export TURTLEBOT3_MODEL=burger
```

Agregarlo al `.bashrc` si todavía no está:

```bash
echo 'export TURTLEBOT3_MODEL=burger' >> ~/.bashrc
source ~/.bashrc
```

Si el profesor usa otro modelo, cambiar `burger` por:

```text
waffle
waffle_pi
```

---

## 3. Configurar red entre laptop y robot

La laptop y el TurtleBot3 deben estar en la misma red WiFi.

En la laptop:

```bash
hostname -I
```

En la Raspberry Pi del robot:

```bash
hostname -I
```

Anotar ambas IPs:

```text
IP_LAPTOP=192.168.X.X
IP_TURTLEBOT=192.168.X.Y
```

Verificar conexión desde la laptop:

```bash
ping IP_TURTLEBOT
```

Ejemplo:

```bash
ping 192.168.1.50
```

Si responde, hay comunicación.

---

## 4. Configurar ROS_DOMAIN_ID

En ROS 2, la laptop y el robot deben usar el mismo `ROS_DOMAIN_ID`.

En la laptop:

```bash
echo 'export ROS_DOMAIN_ID=30' >> ~/.bashrc
source ~/.bashrc
```

En la Raspberry Pi del robot:

```bash
echo 'export ROS_DOMAIN_ID=30' >> ~/.bashrc
source ~/.bashrc
```

Puedes usar otro número, pero debe ser igual en ambos.

Verificar:

```bash
echo $ROS_DOMAIN_ID
```

Debe salir:

```text
30
```

---

## 5. Entrar por SSH al TurtleBot3

Desde la laptop:

```bash
ssh ubuntu@IP_TURTLEBOT
```

Ejemplo:

```bash
ssh ubuntu@192.168.1.50
```

Si pide contraseña, colocar la contraseña configurada en la Raspberry Pi.

---

## 6. Levantar el robot físico con bringup

Dentro de la terminal SSH del TurtleBot3:

```bash
export TURTLEBOT3_MODEL=burger
ros2 launch turtlebot3_bringup robot.launch.py
```

Esta terminal debe quedarse abierta.

Este comando inicia los nodos básicos del robot físico, incluyendo sensores, odometría y comunicación con OpenCR.

---

## 7. Verificar que los tópicos existen

Abrir una nueva terminal en la laptop y ejecutar:

```bash
source /opt/ros/humble/setup.bash
source ~/turtlebot3_ws/install/setup.bash
export TURTLEBOT3_MODEL=burger
ros2 topic list
```

Deben aparecer como mínimo:

```text
/cmd_vel
/odom
/scan
/tf
/tf_static
```

Los tres más importantes para el agente son:

```text
/scan     -> datos del láser LDS
/odom     -> posición/orientación estimada
/cmd_vel  -> velocidades enviadas al robot
```

---

## 8. Verificar datos del láser

En la laptop:

```bash
ros2 topic echo /scan --once
```

Debe mostrar un mensaje tipo `sensor_msgs/msg/LaserScan`.

Revisar que tenga campos como:

```text
angle_min
angle_max
range_min
range_max
ranges
```

Si `/scan` no aparece, el agente no podrá construir el estado.

---

## 9. Verificar odometría

En la laptop:

```bash
ros2 topic echo /odom --once
```

Debe mostrar un mensaje tipo `nav_msgs/msg/Odometry`.

Si `/odom` no aparece, el agente no sabrá cómo cambia la posición/orientación del robot.

---

## 10. Probar movimiento manual antes del agente

Antes de correr cualquier modelo de aprendizaje, probar teleoperación.

En una terminal de la laptop:

```bash
export TURTLEBOT3_MODEL=burger
ros2 run turtlebot3_teleop teleop_keyboard
```

Usar las teclas:

```text
w -> avanzar
x -> retroceder
s -> detener
a -> girar izquierda
d -> girar derecha
space -> freno
CTRL+C -> salir
```

Si el robot responde correctamente, el tópico `/cmd_vel` está funcionando.

---

## 11. Prueba segura de /cmd_vel

Antes de correr el agente, hacer una prueba mínima de velocidad.

En la laptop:

```bash
ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.03}, angular: {z: 0.0}}"
```

El robot debe avanzar muy poco.

Para detenerlo:

```bash
ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.0}, angular: {z: 0.0}}"
```

> Recomendación: hacer esta prueba en el piso, con espacio libre y con una persona lista para levantar o apagar el robot si se mueve mal.

---

## 12. Ajuste importante para Actor-Critic físico

En simulación, el agente puede usar reset de Gazebo.

En físico, no existe:

```text
/reset_simulation
/reset_world
```

Por eso, para el robot físico:

```text
No se usa Gazebo.
No se usa reset_simulation.
No se entrena desde cero al inicio.
Se carga el modelo entrenado.
Se hace inferencia.
Se publica /cmd_vel.
```

El agente físico debe:

```text
1. Leer /scan.
2. Leer /odom.
3. Construir el mismo estado usado en simulación.
4. Cargar el modelo .pt entrenado.
5. Predecir acción continua [v, w].
6. Limitar velocidades por seguridad.
7. Publicar en /cmd_vel.
8. Detenerse si detecta obstáculo muy cerca.
```

---

## 13. Límites de velocidad recomendados para primera prueba

No usar al inicio los máximos de simulación.

Para primera prueba física:

```text
linear_x máximo: 0.03 a 0.06 m/s
angular_z máximo: 0.4 a 0.8 rad/s
```

Ejemplo recomendado:

```python
MAX_LINEAR = 0.05
MAX_ANGULAR = 0.6
```

Cuando funcione de forma estable, recién aumentar poco a poco.

---

## 14. Distancia mínima de seguridad

El robot debe detenerse si el LDS detecta obstáculo muy cerca.

Recomendado:

```text
STOP_DISTANCE = 0.18  # metros
```

Lógica esperada:

```python
if min_laser_distance < STOP_DISTANCE:
    linear_x = 0.0
    angular_z = 0.0
```

Esto evita que el robot choque fuerte durante la prueba real.

---

## 15. Cargar modelo Actor-Critic entrenado

El modelo entrenado desde simulación debería estar en una ruta parecida a:

```bash
~/turtlebot3_a2c_runs/a2c_continuous_turtlebot3.pt
```

Verificar:

```bash
ls ~/turtlebot3_a2c_runs/
```

Debe aparecer:

```text
a2c_continuous_turtlebot3.pt
```

Copiar el modelo al workspace o carpeta de modelos:

```bash
mkdir -p ~/turtlebot3_ws/models/actor_critic
cp ~/turtlebot3_a2c_runs/a2c_continuous_turtlebot3.pt ~/turtlebot3_ws/models/actor_critic/
```

---

## 16. Ejecutar política entrenada en robot físico

Este comando depende del nombre final del nodo de inferencia.

Si el paquete tiene un nodo tipo `run_policy`, la ejecución sería:

```bash
source /opt/ros/humble/setup.bash
source ~/turtlebot3_ws/install/setup.bash
export TURTLEBOT3_MODEL=burger
ros2 run turtlebot3_a2c run_policy --ros-args \
  -p model_path:=$HOME/turtlebot3_ws/models/actor_critic/a2c_continuous_turtlebot3.pt \
  -p real_robot:=true \
  -p max_linear:=0.05 \
  -p max_angular:=0.6 \
  -p stop_distance:=0.18
```

Si todavía no existe `run_policy`, se debe crear un nodo separado para inferencia física. No conviene usar el nodo de entrenamiento directamente en el robot real.

---

## 17. Orden recomendado de terminales para robot físico

### Terminal 1: SSH al robot y bringup

```bash
ssh ubuntu@IP_TURTLEBOT
export TURTLEBOT3_MODEL=burger
ros2 launch turtlebot3_bringup robot.launch.py
```

Dejar abierta.

### Terminal 2: verificar tópicos desde laptop

```bash
source /opt/ros/humble/setup.bash
source ~/turtlebot3_ws/install/setup.bash
ros2 topic list
```

Confirmar:

```text
/scan
/odom
/cmd_vel
```

### Terminal 3: prueba manual

```bash
export TURTLEBOT3_MODEL=burger
ros2 run turtlebot3_teleop teleop_keyboard
```

Mover poquito y detener.

### Terminal 4: correr política Actor-Critic entrenada

```bash
ros2 run turtlebot3_a2c run_policy --ros-args \
  -p model_path:=$HOME/turtlebot3_ws/models/actor_critic/a2c_continuous_turtlebot3.pt \
  -p real_robot:=true \
  -p max_linear:=0.05 \
  -p max_angular:=0.6 \
  -p stop_distance:=0.18
```

---

## 18. Qué NO hacer en la primera prueba física

No hacer esto al inicio:

```text
No entrenar desde cero en el robot físico.
No usar velocidades máximas.
No probar sobre una mesa.
No correr el agente sin verificar /scan.
No correr el agente sin verificar /odom.
No correr el agente sin botón/freno de emergencia.
No usar reset_simulation en físico.
```

---

## 19. Checklist antes de correr el agente

Antes de ejecutar Actor-Critic en el robot físico, marcar:

```text
[ ] Laptop y robot en la misma red WiFi.
[ ] Puedo hacer ping al robot.
[ ] Puedo entrar por SSH.
[ ] ROS_DOMAIN_ID es igual en laptop y robot.
[ ] TURTLEBOT3_MODEL=burger en laptop y robot.
[ ] Bringup corre sin error.
[ ] /scan aparece en ros2 topic list.
[ ] /odom aparece en ros2 topic list.
[ ] /cmd_vel aparece en ros2 topic list.
[ ] Teleop funciona.
[ ] El robot puede frenar con space/s.
[ ] El modelo .pt existe.
[ ] Velocidades limitadas para prueba física.
[ ] Hay espacio libre alrededor del robot.
```

---

## 20. Errores comunes

### Error: no aparece `/scan`

Revisar bringup:

```bash
ros2 launch turtlebot3_bringup robot.launch.py
```

Revisar conexión del LDS y OpenCR.

---

### Error: no aparece `/odom`

Revisar que OpenCR esté conectado y que el bringup no haya fallado.

---

### Error: la laptop no ve tópicos del robot

Verificar:

```bash
echo $ROS_DOMAIN_ID
```

Debe ser igual en laptop y Raspberry Pi.

También verificar red:

```bash
ping IP_TURTLEBOT
```

---

### Error: el robot no se mueve con `/cmd_vel`

Probar teleop:

```bash
ros2 run turtlebot3_teleop teleop_keyboard
```

Si teleop tampoco mueve el robot, el problema no es el agente; es bringup, OpenCR, batería, motores o comunicación.

---

### Error: el robot se mueve muy agresivo

Bajar límites:

```text
max_linear = 0.03
max_angular = 0.4
```

---

## 21. Diferencia entre simulación y físico

| Simulación | Robot físico |
|---|---|
| Usa Gazebo | No usa Gazebo |
| Usa `/reset_simulation` | No hay reset automático |
| Entrena muchos episodios | Primero solo inferencia |
| El robot puede chocar sin daño | El choque puede dañar piezas |
| Sensores ideales o simulados | Sensores con ruido real |
| Velocidades pueden ser mayores | Velocidades bajas al inicio |

---

## 22. Resumen rápido

### En el robot

```bash
ssh ubuntu@IP_TURTLEBOT
export TURTLEBOT3_MODEL=burger
ros2 launch turtlebot3_bringup robot.launch.py
```

### En la laptop

```bash
source /opt/ros/humble/setup.bash
source ~/turtlebot3_ws/install/setup.bash
export TURTLEBOT3_MODEL=burger
ros2 topic list
```

### Verificar sensores

```bash
ros2 topic echo /scan --once
ros2 topic echo /odom --once
```

### Probar movimiento manual

```bash
ros2 run turtlebot3_teleop teleop_keyboard
```

### Correr política entrenada

```bash
ros2 run turtlebot3_a2c run_policy --ros-args \
  -p model_path:=$HOME/turtlebot3_ws/models/actor_critic/a2c_continuous_turtlebot3.pt \
  -p real_robot:=true \
  -p max_linear:=0.05 \
  -p max_angular:=0.6 \
  -p stop_distance:=0.18
```

---

## 23. Referencias oficiales

- ROBOTIS e-Manual: TurtleBot3 Bringup
- ROBOTIS e-Manual: TurtleBot3 SBC Setup
- ROBOTIS e-Manual: TurtleBot3 Basic Operation / Teleoperation
- ROBOTIS e-Manual: LDS-01 Laser Distance Sensor
