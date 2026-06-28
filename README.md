# Instrucciones de Ejecución - TurtleBot3 A2C + DAgger
**Práctica Lab 4: Sim to Real | ROS 2 Humble + Gazebo + PyTorch**

El sistema integra ROS 2 Humble,Gazebo y PyTorch para entrenar un agente Actor-Critic (A2C) con acción continua y corregirlo mediante el algoritmo DAgger con intervención de un experto humano.

La misión del robot es navegar hacia una meta fija en la posición (1.5, 1.5) evadiendo obstáculos móviles. El espacio de acción es continuo: velocidad lineal v ∈ [0, 0.12] m/s y velocidad angular ω ∈ [-1.2, 1.2] rad/s.

---

## Setup base (ejecutar siempre antes de cualquier nodo)

Antes de lanzar cualquier nodo en la laptop, es obligatorio cargar el entorno
de ROS 2 Humble y el workspace compilado. Sin esto, los comandos `ros2 run`
no encontrarán el paquete `turtlebot3_a2c`.

```bash
cd ~/turtlebot3_ws
source /opt/ros/humble/setup.bash
source install/setup.bash
export TURTLEBOT3_MODEL=burger
```

---

## Simulación

La simulación requiere siempre dos terminales en paralelo:
Terminal 1 con Gazebo corriendo, y Terminal 2 con el nodo del agente.

### Terminal 1 — Abrir Gazebo

Lanza el entorno de simulación Stage 4, que incluye el TurtleBot3 Burger
y obstáculos móviles. La meta fija aparece como un cubo verde en (1.5, 1.5).
Esperar hasta que el robot aparezca en escena antes de lanzar el agente.

```bash
cd ~/turtlebot3_ws
source /opt/ros/humble/setup.bash
source install/setup.bash
export TURTLEBOT3_MODEL=burger
ros2 launch turtlebot3_gazebo turtlebot3_dqn_stage4.launch.py
```

---

### Terminal 2 — Entrenar A2C

Entrena el agente A2C desde cero con acción continua (política Gaussiana).
El agente aprende a predecir (v, ω) mediante Advantage Actor-Critic con GAE.
El log se guarda en `train_log.txt` para generar las gráficas del reporte.
El entrenamiento puede detenerse con Ctrl+C en cualquier momento; el modelo
se guarda automáticamente cada 50 episodios y al terminar.

```bash
cd ~/turtlebot3_ws
source /opt/ros/humble/setup.bash
source install/setup.bash
export TURTLEBOT3_MODEL=burger
export PYTHONUNBUFFERED=1
ros2 run turtlebot3_a2c train_a2c 2>&1 | tee ~/turtlebot3_ws/reporte/train_log.txt
```

Salida esperada por episodio:
```
Ep    1 | reward  -102.41 | collision | exitos 0
   update | L_actor +0.064 | L_critic +45.877 | H +2.960
```

Modelo guardado en: `~/turtlebot3_ws/a2c_models/a2c_sim.pth`

---

### Terminal 2 — Ejecutar A2C entrenado (inferencia)

Carga el modelo `a2c_sim.pth` y lo ejecuta en modo determinista (usa la media
de la distribución Gaussiana, sin muestreo). Sirve para validar el comportamiento
aprendido y mostrar los fallos de A2C antes de aplicar DAgger.

```bash
cd ~/turtlebot3_ws
source /opt/ros/humble/setup.bash
source install/setup.bash
export TURTLEBOT3_MODEL=burger
ros2 run turtlebot3_a2c run_a2c
```

---

### Terminal 2 — Ejecutar DAgger con experto humano

Implementa el algoritmo Dataset Aggregation (DAgger). El agente A2C pilotea
en modo automático; el humano puede tomar el control en cualquier momento con
el teclado para corregir la trayectoria. Los pares (estado, acción experta)
se capturan y se usa fine-tuning por imitación (MSE) para actualizar la red.
El log se guarda para generar la gráfica de tasa de intervención del reporte.

```bash
cd ~/turtlebot3_ws
source /opt/ros/humble/setup.bash
source install/setup.bash
export TURTLEBOT3_MODEL=burger
ros2 run turtlebot3_a2c run_dagger 2>&1 | tee ~/turtlebot3_ws/reporte/dagger_log.txt
```

**Controles DAgger:**

| Tecla | Acción |
|-------|--------|
| `i` | Alternar AUTO ↔ HUMANO (intervención) |
| `w` | Aumentar velocidad lineal (avanzar) |
| `x` | Reducir velocidad lineal |
| `a` | Girar izquierda (ω positivo) |
| `d` | Girar derecha (ω negativo) |
| `s` | Detener robot (v=0, ω=0) |
| `t` | Ejecutar fine-tuning con pares capturados |
| `r` | Reiniciar episodio |
| `q` | Guardar modelo y salir |

**Flujo recomendado por ronda:**
1. Dejar en AUTO unos segundos (observar fallo de A2C)
2. Pulsar `i` → modo HUMANO
3. Conducir hacia el cubo verde con `w/a/d` durante 60+ segundos
4. Pulsar `t` → esperar mensaje: `Fine-tuning hecho con N pares | loss imitacion 0.XXXX`
5. Pulsar `i` → volver a AUTO y observar mejora
6. Repetir 2-3 rondas para ver la tasa de intervención decrecer
7. Pulsar `q` para guardar

Modelo guardado en: `~/turtlebot3_ws/a2c_models/a2c_dagger.pth`

---

### Generar gráficas A2C

Lee el log del entrenamiento y genera dos imágenes para el reporte:
la curva de recompensa acumulada por episodio y las curvas de pérdida
del Actor y Crítico. Requiere haber entrenado y guardado `train_log.txt`.

```bash
cd ~/turtlebot3_ws/reporte
python3 generar_graficas.py train_log.txt
# Genera:
#   graficas/recompensa_vs_episodios.png  → Fase 1 del reporte
#   graficas/curvas_perdida.png           → Fase 1 del reporte
```

### Generar gráficas DAgger

Lee el log de DAgger y genera la gráfica de tasa de intervención humana
por ronda (requerida por el enunciado: debe ser decreciente) y la curva
de loss de imitación. Requiere haber ejecutado DAgger con el `tee`.

```bash
cd ~/turtlebot3_ws/reporte
python3 generar_graficas_dagger.py dagger_log.txt
# Genera:
#   graficas/dagger_intervencion.png  → Tasa intervención (Fase 2 del reporte)
#   graficas/dagger_loss.png          → Loss de imitación por ronda
```

---

### Verificar modelos guardados

```bash
ls ~/turtlebot3_ws/a2c_models/
# Debe mostrar:
#   a2c_sim.pth      → modelo base entrenado con A2C
#   a2c_dagger.pth   → modelo corregido con DAgger (debe ser distinto a a2c_sim.pth)
```

---

## Robot físico (TurtleBot4 Lite — ROS 2 Jazzy)

El mismo código de simulación se despliega en el robot real sin modificaciones,
apuntando a los tópicos físicos. El robot usa ROS 2 Jazzy mientras la laptop
usa ROS 2 Humble; la comunicación se realiza por DDS en la misma red local
con `ROS_DOMAIN_ID=4`. El Reality Gap (ruido del LiDAR, fricción del suelo,
retardo de motores) hace que la política de simulación falle en el robot real,
motivando la corrección con DAgger en el entorno físico.

> **Importante:** No abrir Gazebo cuando se trabaja en modo físico.

### Paso 1 — Conectar al robot (desde laptop)

```bash
ssh ubuntu@turtlebot4.local
# Si falla por hostname:
ssh ubuntu@10.42.0.1
```

### Paso 2 — Bringup en el robot

Inicializa todos los drivers del TurtleBot4 Lite: LiDAR, odometría y motores.
Dejar esta terminal abierta durante toda la sesión.

```bash
source /opt/ros/jazzy/setup.bash
export ROS_DOMAIN_ID=4
ros2 launch turtlebot4_bringup lite.launch.py
```

### Paso 3 — Verificar comunicación (laptop)

Confirma que los tópicos del robot llegan a la laptop antes de lanzar el agente.
Deben aparecer `/scan`, `/odom` y `/cmd_vel` o `/cmd_vel_unstamped`.

```bash
source /opt/ros/humble/setup.bash
source ~/turtlebot3_ws/install/setup.bash
export ROS_DOMAIN_ID=4
ros2 topic list | grep -E "scan|odom|cmd"
```

### Paso 4 — A2C en físico (zero-shot)

Carga `a2c_sim.pth` y ejecuta inferencia sobre el robot real. El remap
`/cmd_vel → /cmd_vel_unstamped` es necesario porque el TurtleBot4 usa
`Twist` sin header en ese tópico.

```bash
source /opt/ros/humble/setup.bash
source ~/turtlebot3_ws/install/setup.bash
export ROS_DOMAIN_ID=4
ros2 run turtlebot3_a2c run_a2c --ros-args -r /cmd_vel:=/cmd_vel_unstamped
```

### Paso 5 — DAgger en físico

Mismo script de simulación, ahora capturando experiencia real corregida.
El experto interviene cuando el robot falla por el Reality Gap y el fine-tuning
adapta la red al entorno físico in situ.

```bash
source /opt/ros/humble/setup.bash
source ~/turtlebot3_ws/install/setup.bash
export ROS_DOMAIN_ID=4
ros2 run turtlebot3_a2c run_dagger --ros-args -r /cmd_vel:=/cmd_vel_unstamped
```

### Parada de emergencia

Tener siempre esta terminal lista para detener el robot inmediatamente.

```bash
source /opt/ros/humble/setup.bash
export ROS_DOMAIN_ID=4
ros2 topic pub --once /cmd_vel_unstamped geometry_msgs/msg/Twist \
  "{linear: {x: 0.0, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}"
```

---

## Ejecutables del paquete

```bash
ros2 pkg executables turtlebot3_a2c
# turtlebot3_a2c train_a2c   → entrenamiento A2C
# turtlebot3_a2c run_a2c     → inferencia A2C
# turtlebot3_a2c run_dagger  → DAgger con experto humano
```

---
