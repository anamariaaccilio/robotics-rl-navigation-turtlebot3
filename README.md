# TurtleBot3 RL en ROS 2 Humble: DQN y Actor-Critic continuo

Este README deja documentado el flujo completo para ejecutar los dos casos del proyecto:

1. **DQN oficial de ROBOTIS**, ya probado y funcionando en Gazebo.
2. **Actor-Critic continuo / A2C**, como nuevo agente para simulación.

La idea es que no tengas que volver a buscar comandos en el chat. Copia y pega por bloques.

---

## 0. Supuestos del entorno

Este documento asume que estás trabajando en:

- Ubuntu 22.04 Jammy.
- ROS 2 Humble.
- TurtleBot3 Burger.
- Workspace principal: `~/turtlebot3_ws`.
- Simulador: Gazebo clásico.
- Etapa de prueba: `turtlebot3_dqn_stage4.launch.py`.
- Sin GPU NVIDIA, por eso en DQN se usa `use_gpu:=false`.

Tu workspace debe tener esta estructura base:

```bash
~/turtlebot3_ws/src/
├── turtlebot3
├── turtlebot3_msgs
├── turtlebot3_simulations
├── turtlebot3_machine_learning
└── turtlebot3_a2c              # solo si ya instalaste Actor-Critic
```

---

## 1. Comandos base que deben estar configurados

Ejecuta esto una sola vez para asegurar que cada terminal nueva cargue ROS, tu workspace y el modelo Burger:

```bash
grep -qxF 'source /opt/ros/humble/setup.bash' ~/.bashrc || echo 'source /opt/ros/humble/setup.bash' >> ~/.bashrc
grep -qxF 'source ~/turtlebot3_ws/install/setup.bash' ~/.bashrc || echo 'source ~/turtlebot3_ws/install/setup.bash' >> ~/.bashrc
grep -qxF 'export TURTLEBOT3_MODEL=burger' ~/.bashrc || echo 'export TURTLEBOT3_MODEL=burger' >> ~/.bashrc
source ~/.bashrc
```

Verifica:

```bash
echo $TURTLEBOT3_MODEL
ros2 pkg list | grep turtlebot3
```

Debe mostrar `burger` y varios paquetes de TurtleBot3.

---

## 2. Compilar el workspace completo

Usa esto cuando clones paquetes nuevos, modifiques configuración o quieras asegurar que todo esté bien:

```bash
cd ~/turtlebot3_ws
colcon build --symlink-install
source ~/turtlebot3_ws/install/setup.bash
```

Si al final aparece algo como esto, está bien:

```text
Summary: XX packages finished
```

Si aparecen paquetes con `stderr output`, pero no aparece `failed`, normalmente son warnings y no bloquean.

---

## 3. Configuración importante del láser para DQN

El DQN oficial espera un estado de **26 valores**:

- 24 valores del láser frontal.
- Distancia a la meta.
- Ángulo hacia la meta.

Como el entorno toma la mitad frontal del barrido, el modelo debe tener:

```xml
<samples>48</samples>
<resolution>1.000000</resolution>
<min_angle>0.000000</min_angle>
<max_angle>6.280000</max_angle>
```

Archivo a revisar:

```bash
gedit ~/turtlebot3_ws/src/turtlebot3_simulations/turtlebot3_gazebo/models/turtlebot3_burger/model.sdf
```

Busca `samples` con `Ctrl + F` y verifica que esté en `48`.

También puedes verificar por terminal:

```bash
grep -n -A4 "samples" ~/turtlebot3_ws/src/turtlebot3_simulations/turtlebot3_gazebo/models/turtlebot3_burger/model.sdf
```

Debe salir algo como:

```xml
<samples>48</samples>
<resolution>1.000000</resolution>
<min_angle>0.000000</min_angle>
<max_angle>6.280000</max_angle>
```

Si modificas este archivo, recompila:

```bash
cd ~/turtlebot3_ws
colcon build --symlink-install
source ~/turtlebot3_ws/install/setup.bash
```

### Error típico del láser

Si en DQN aparece:

```text
ValueError: cannot reshape array of size 182 into shape (1,26)
```

o:

```text
ValueError: cannot reshape array of size 14 into shape (1,26)
```

entonces el láser no está entregando el tamaño esperado. Revisa que `samples` sea `48` y `max_angle` sea `6.280000`.

---

# CASO 1: Ejecutar DQN oficial

## 4. Antes de correr DQN

Asegúrate de cerrar cualquier ejecución anterior:

- En cada terminal activa presiona `Ctrl + C`.
- Cierra la ventana de Gazebo si sigue abierta.

También puedes matar procesos de Gazebo si se quedan colgados:

```bash
killall -9 gzserver gzclient 2>/dev/null
```

---

## 5. DQN requiere 4 terminales

No necesitas ubicarte en ninguna carpeta específica si tu `.bashrc` está bien configurado. Solo abre terminales nuevas.

---

## Terminal 1: abrir Gazebo con el stage 4

```bash
source ~/.bashrc
ros2 launch turtlebot3_gazebo turtlebot3_dqn_stage4.launch.py
```

Espera a que se abra Gazebo con el robot en el laberinto. No cierres esta terminal.

---

## Terminal 2: lanzar el nodo de Gazebo para DQN

```bash
source ~/.bashrc
ros2 run turtlebot3_dqn dqn_gazebo 4
```

Este nodo se encarga de la lógica de meta/tarea en Gazebo.

---

## Terminal 3: lanzar el entorno DQN

```bash
source ~/.bashrc
ros2 run turtlebot3_dqn dqn_environment
```

Este nodo calcula estados, recompensas y finalización del episodio.

---

## Terminal 4: lanzar el agente DQN

Como no tienes GPU NVIDIA, usa `use_gpu:=false`:

```bash
source ~/.bashrc
ros2 run turtlebot3_dqn dqn_agent --ros-args \
  -p epsilon_decay:=6000 \
  -p max_training_episodes:=1000 \
  -p use_gpu:=false \
  -p model_file:=model1.h5 \
  -p verbose:=true
```

Versión en una sola línea:

```bash
ros2 run turtlebot3_dqn dqn_agent --ros-args -p epsilon_decay:=6000 -p max_training_episodes:=1000 -p use_gpu:=false -p model_file:=model1.h5 -p verbose:=true
```

---

## 6. Señales de que DQN está funcionando

En la terminal del agente deberías ver episodios, recompensas y mensajes como:

```text
Episode: ...
score: ...
epsilon: ...
Goal Reached
service for task succeed finished
```

En Gazebo deberías ver el robot moviéndose y buscando la meta.

---

# CASO 2: Ejecutar Actor-Critic continuo / A2C

Este caso usa un paquete aparte llamado:

```text
turtlebot3_a2c
```

La idea es no romper el DQN oficial. DQN queda en `turtlebot3_machine_learning`; Actor-Critic queda en `turtlebot3_a2c`.

---

## 7. Instalar el paquete Actor-Critic desde cero

Si tienes intentos anteriores incompletos, bórralos:

```bash
cd ~/turtlebot3_ws/src
rm -rf turtlebot3_a2c
```

Luego copia o descomprime el paquete `turtlebot3_a2c` dentro de:

```bash
~/turtlebot3_ws/src/
```

La estructura final debe ser:

```bash
~/turtlebot3_ws/src/turtlebot3_a2c/
├── README.md
├── package.xml
├── setup.cfg
├── setup.py
├── resource
│   └── turtlebot3_a2c
└── turtlebot3_a2c
    ├── __init__.py
    ├── a2c_agent.py
    ├── environment.py
    ├── networks.py
    ├── settings.py
    └── utils.py
```

Verifica la parte externa:

```bash
ls ~/turtlebot3_ws/src/turtlebot3_a2c
```

Debe mostrar:

```text
README.md  package.xml  resource  setup.cfg  setup.py  turtlebot3_a2c
```

Verifica la parte interna:

```bash
ls ~/turtlebot3_ws/src/turtlebot3_a2c/turtlebot3_a2c
```

Debe mostrar:

```text
__init__.py  a2c_agent.py  environment.py  networks.py  settings.py  utils.py
```

---

## 8. Instalar PyTorch para Actor-Critic

Como no tienes GPU, instala PyTorch CPU:

```bash
pip install torch numpy --break-system-packages
```

Verifica:

```bash
python3 - << 'PY'
import torch
print('Torch:', torch.__version__)
print('CUDA disponible:', torch.cuda.is_available())
PY
```

Debe decir `CUDA disponible: False`. Eso está bien.

---

## 9. Compilar solo Actor-Critic

```bash
cd ~/turtlebot3_ws
colcon build --symlink-install --packages-select turtlebot3_a2c
source ~/turtlebot3_ws/install/setup.bash
```

Debe terminar con:

```text
Summary: 1 package finished
```

Si ROS no encuentra el paquete, vuelve a ejecutar:

```bash
source /opt/ros/humble/setup.bash
source ~/turtlebot3_ws/install/setup.bash
ros2 pkg list | grep turtlebot3_a2c
```

---

## 10. Actor-Critic requiere 2 terminales

A diferencia de DQN, aquí solo usas:

1. Gazebo.
2. Agente Actor-Critic.

No ejecutes al mismo tiempo los nodos del DQN (`dqn_gazebo`, `dqn_environment`, `dqn_agent`) mientras pruebas Actor-Critic.

---

## Terminal 1: abrir Gazebo

```bash
source ~/.bashrc
export TURTLEBOT3_MODEL=burger
ros2 launch turtlebot3_gazebo turtlebot3_dqn_stage4.launch.py
```

Espera a que Gazebo abra el laberinto.

---

## Terminal 2: entrenar Actor-Critic

```bash
source ~/turtlebot3_ws/install/setup.bash
ros2 run turtlebot3_a2c train
```

Para una prueba corta:

```bash
ros2 run turtlebot3_a2c train --ros-args -p episodes:=50
```

---

## 11. Señales de que Actor-Critic está funcionando

En la terminal del agente deberías ver algo parecido a:

```text
Ep 0001 | reward=... | steps=... | status=running/collision/success | dist=...
Ep 0002 | reward=... | steps=... | status=...
```

En Gazebo deberías ver que el robot publica velocidades continuas:

- Velocidad lineal `v`.
- Velocidad angular `w`.

Esto ya no es DQN discreto de 5 acciones; el actor produce acciones continuas dentro de límites seguros.

---

## 12. Archivos generados por Actor-Critic

Los entrenamientos pueden guardar resultados en una carpeta como:

```bash
~/turtlebot3_a2c_runs/
```

Archivos esperados:

```text
a2c_continuous_turtlebot3.pt
a2c_training_log.csv
```

Verifica:

```bash
ls ~/turtlebot3_a2c_runs/
```

---

# Comparación DQN vs Actor-Critic

Para tu informe o exposición, compara:

| Métrica | DQN | Actor-Critic continuo |
|---|---:|---:|
| ¿Llega a la meta? | Sí/No | Sí/No |
| Tiempo hasta llegar | segundos o pasos | segundos o pasos |
| Recompensa promedio | score promedio | reward promedio |
| Colisiones | número de choques | número de choques |
| Tipo de acción | discreta | continua |
| Red neuronal | Q-network | Actor + Critic |
| Framework | TensorFlow/Keras | PyTorch |

DQN elige una acción discreta. Actor-Critic continuo genera directamente velocidad lineal y angular, lo cual se parece más al control real del robot.

---

# Comandos útiles de diagnóstico

## Ver paquetes instalados

```bash
ros2 pkg list | grep turtlebot3
```

## Buscar el agente DQN original

```bash
find ~/turtlebot3_ws/src/turtlebot3_machine_learning -name "dqn_agent.py"
```

## Abrir el agente DQN

```bash
gedit ~/turtlebot3_ws/src/turtlebot3_machine_learning/turtlebot3_dqn/turtlebot3_dqn/dqn_agent.py
```

## Abrir el agente Actor-Critic

```bash
gedit ~/turtlebot3_ws/src/turtlebot3_a2c/turtlebot3_a2c/a2c_agent.py
```

## Abrir configuración Actor-Critic

```bash
gedit ~/turtlebot3_ws/src/turtlebot3_a2c/turtlebot3_a2c/settings.py
```

## Recompilar solo Actor-Critic

```bash
cd ~/turtlebot3_ws
colcon build --symlink-install --packages-select turtlebot3_a2c
source ~/turtlebot3_ws/install/setup.bash
```

## Recompilar todo

```bash
cd ~/turtlebot3_ws
colcon build --symlink-install
source ~/turtlebot3_ws/install/setup.bash
```

## Cerrar Gazebo si se queda colgado

```bash
killall -9 gzserver gzclient 2>/dev/null
```

## Limpiar compilación completa si algo queda raro

Usar solo si hay errores difíciles de resolver:

```bash
cd ~/turtlebot3_ws
rm -rf build install log
colcon build --symlink-install
source ~/turtlebot3_ws/install/setup.bash
```

Luego vuelve a verificar:

```bash
ros2 pkg list | grep turtlebot3
```

---

# Flujo recomendado de trabajo

## Para probar DQN

```bash
# Terminal 1
ros2 launch turtlebot3_gazebo turtlebot3_dqn_stage4.launch.py

# Terminal 2
ros2 run turtlebot3_dqn dqn_gazebo 4

# Terminal 3
ros2 run turtlebot3_dqn dqn_environment

# Terminal 4
ros2 run turtlebot3_dqn dqn_agent --ros-args -p epsilon_decay:=6000 -p max_training_episodes:=1000 -p use_gpu:=false -p model_file:=model1.h5 -p verbose:=true
```

## Para probar Actor-Critic

Primero cierra DQN y Gazebo con `Ctrl + C`.

```bash
# Terminal 1
ros2 launch turtlebot3_gazebo turtlebot3_dqn_stage4.launch.py

# Terminal 2
ros2 run turtlebot3_a2c train
```

---

# Errores comunes y solución rápida

## Error: `package turtlebot3_a2c not found`

Solución:

```bash
cd ~/turtlebot3_ws
colcon build --symlink-install --packages-select turtlebot3_a2c
source ~/turtlebot3_ws/install/setup.bash
ros2 pkg list | grep turtlebot3_a2c
```

## Error: `No executable found`

Revisa que `setup.py` tenga el entry point:

```python
entry_points={
    'console_scripts': [
        'train = turtlebot3_a2c.a2c_agent:main',
    ],
},
```

Luego recompila:

```bash
cd ~/turtlebot3_ws
colcon build --symlink-install --packages-select turtlebot3_a2c
source ~/turtlebot3_ws/install/setup.bash
```

## Error de reshape en DQN

Revisar láser:

```bash
grep -n -A4 "samples" ~/turtlebot3_ws/src/turtlebot3_simulations/turtlebot3_gazebo/models/turtlebot3_burger/model.sdf
```

Debe ser:

```xml
<samples>48</samples>
<max_angle>6.280000</max_angle>
```

## Gazebo abre pero el robot no se mueve

Verifica que no tengas mezclados nodos DQN y Actor-Critic al mismo tiempo. Cierra todo:

```bash
killall -9 gzserver gzclient 2>/dev/null
```

Luego vuelve a correr solo el caso que quieres probar.

---

# Resumen rápido

DQN:

- Usa 4 terminales.
- Usa `turtlebot3_dqn`.
- Usa `use_gpu:=false` en tu PC.
- Requiere láser con `samples=48`.

Actor-Critic:

- Usa 2 terminales.
- Usa `turtlebot3_a2c`.
- Usa PyTorch CPU.
- Produce acciones continuas `v` y `w`.
- No se corre junto con los nodos DQN.

