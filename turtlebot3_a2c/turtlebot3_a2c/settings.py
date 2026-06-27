# ====================================================================
#  ESTADO Y ACCION
# ====================================================================
N_SCAN = 24
STATE_DIM = N_SCAN + 2          # laser + distancia + angulo  -> 26
ACTION_DIM = 2                  # [velocidad_lineal, velocidad_angular]
MAX_LIDAR_RANGE = 3.5

V_MAX = 0.12                    # m/s  (limite cinematico del burger)
W_MAX = 1.2                     # rad/s

# ====================================================================
#  ENTORNO / EPISODIO
# ====================================================================
GOAL_REACHED_DIST = 0.20
COLLISION_DIST    = 0.20
OBSTACLE_NEAR     = 0.30
MAX_STEPS         = 500
CONTROL_PERIOD    = 0.10        # s (10 Hz)

GOAL_X_RANGE = (-1.8, 1.8)
GOAL_Y_RANGE = (-1.8, 1.8)

# Meta FIJA (consigna 4.1: "avance hacia la meta fija")
USE_FIXED_GOAL = True
FIXED_GOAL = (1.5, 1.5)

# ====================================================================
#  RECOMPENSA (= criterio de evaluacion)
# ====================================================================
K_PROGRESS     = 20.0           # premio por acercarse a la meta
STEP_PENALTY   = 0.05           # castigo por paso -> rapidez
K_TURN         = 0.05           # castigo a giros innecesarios (|w|)
K_OBSTACLE     = 5.0            # castigo por cercania de obstaculos
SUCCESS_REWARD = 200.0          # premio por llegar
COLLISION_REWARD = -150.0       # castigo drastico por chocar

# ====================================================================
#  HIPERPARAMETROS A2C
# ====================================================================
GAMMA          = 0.99
GAE_LAMBDA     = 0.95
LR             = 3e-4
C_VALUE        = 0.5
C_ENTROPY      = 0.01
MAX_GRAD_NORM  = 0.5
HIDDEN         = 256
ROLLOUT_STEPS  = 512
MAX_EPISODES   = 3000
SAVE_EVERY     = 50
USE_STATE_NORM = True

# ====================================================================
#  ROS / GAZEBO
# ====================================================================
TOPIC_SCAN   = "/scan"
TOPIC_ODOM   = "/odom"
TOPIC_CMDVEL = "/cmd_vel"
RESET_SERVICE = "/reset_simulation"

GOAL_VISUALIZE = False
GOAL_ENTITY_NAME = "goal_box"
SET_ENTITY_SERVICE = "/gazebo/set_entity_state"

# ====================================================================
#  MODELO
# ====================================================================
MODEL_DIR = "a2c_models"
MODEL_NAME = "a2c_sim"          # consigna: a2c_sim.pth