import math
import time
import random
import numpy as np
import gymnasium as gym

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import LaserScan
from nav_msgs.msg import Odometry
from geometry_msgs.msg import Twist
from std_srvs.srv import Empty

from . import settings as S


def _euler_yaw_from_quaternion(q):
    siny = 2.0 * (q.w * q.z + q.x * q.y)
    cosy = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
    return math.atan2(siny, cosy)


def _normalize_angle(a):
    while a > math.pi:
        a -= 2.0 * math.pi
    while a < -math.pi:
        a += 2.0 * math.pi
    return a


class Turtlebot3Env(Node, gym.Env):
    def __init__(self):
        Node.__init__(self, 'turtlebot3_a2c_env')

        # ---- Espacios Gymnasium (consigna: gym.spaces.Box) ----
        self.action_space = gym.spaces.Box(
            low=np.array([0.0, -S.W_MAX], dtype=np.float32),
            high=np.array([S.V_MAX, S.W_MAX], dtype=np.float32), dtype=np.float32)
        self.observation_space = gym.spaces.Box(
            low=-np.inf, high=np.inf, shape=(S.STATE_DIM,), dtype=np.float32)

        # ---- ROS ----
        self.cmd_pub = self.create_publisher(Twist, S.TOPIC_CMDVEL, 10)
        self.create_subscription(LaserScan, S.TOPIC_SCAN, self._scan_cb, 10)
        self.create_subscription(Odometry, S.TOPIC_ODOM, self._odom_cb, 10)
        self.reset_client = self.create_client(Empty, S.RESET_SERVICE)

        # ---- (opcional) mover el cubo-meta para verlo en Gazebo ----
        self.set_entity_client = None
        if S.GOAL_VISUALIZE:
            try:
                from gazebo_msgs.srv import SetEntityState
                self._SetEntityState = SetEntityState
                self.set_entity_client = self.create_client(
                    SetEntityState, S.SET_ENTITY_SERVICE)
            except Exception as e:  # noqa
                self.get_logger().warn(f'Goal viz desactivada: {e}')
                self.set_entity_client = None

        # ---- Buffers de sensores ----
        self.scan_ranges = None
        self.position = (0.0, 0.0)
        self.yaw = 0.0

        # ---- Estado del episodio ----
        self.goal = (1.0, 0.0)
        self.prev_distance = None
        self.steps = 0

    # ---------------- Callbacks ----------------
    def _scan_cb(self, msg):
        ranges = np.array(msg.ranges, dtype=np.float32)
        ranges = np.nan_to_num(ranges, nan=S.MAX_LIDAR_RANGE,
                               posinf=S.MAX_LIDAR_RANGE, neginf=0.0)
        ranges = np.clip(ranges, 0.0, S.MAX_LIDAR_RANGE)
        if ranges.size == 0:
            return
        sectors = np.array_split(ranges, S.N_SCAN)
        self.scan_ranges = np.array([s.min() for s in sectors], dtype=np.float32)

    def _odom_cb(self, msg):
        p = msg.pose.pose.position
        self.position = (p.x, p.y)
        self.yaw = _euler_yaw_from_quaternion(msg.pose.pose.orientation)

    # ---------------- Helpers ----------------
    def _distance_to_goal(self):
        dx = self.goal[0] - self.position[0]
        dy = self.goal[1] - self.position[1]
        return math.hypot(dx, dy)

    def _heading_error(self):
        dx = self.goal[0] - self.position[0]
        dy = self.goal[1] - self.position[1]
        return _normalize_angle(math.atan2(dy, dx) - self.yaw)

    def _build_state(self):
        if self.scan_ranges is None:
            self.scan_ranges = np.full(S.N_SCAN, S.MAX_LIDAR_RANGE, dtype=np.float32)
        laser = self.scan_ranges / S.MAX_LIDAR_RANGE
        diag = math.hypot(S.GOAL_X_RANGE[1] - S.GOAL_X_RANGE[0],
                          S.GOAL_Y_RANGE[1] - S.GOAL_Y_RANGE[0])
        dist_norm = self._distance_to_goal() / max(diag, 1e-6)
        angle_norm = self._heading_error() / math.pi
        return np.concatenate([laser, [dist_norm, angle_norm]]).astype(np.float32)

    def _publish_velocity(self, v, w):
        t = Twist()
        t.linear.x = float(v)
        t.angular.z = float(w)
        self.cmd_pub.publish(t)

    def _stop_robot(self):
        self._publish_velocity(0.0, 0.0)

    def _call_reset(self):
        if not self.reset_client.wait_for_service(timeout_sec=3.0):
            self.get_logger().warn(f'Servicio {S.RESET_SERVICE} no disponible')
            return
        self.reset_client.call_async(Empty.Request())

    def _sample_goal(self):
        if getattr(S, 'USE_FIXED_GOAL', True):
            self.goal = tuple(S.FIXED_GOAL)              # meta FIJA (consigna)
        else:
            self.goal = (random.uniform(*S.GOAL_X_RANGE),
                         random.uniform(*S.GOAL_Y_RANGE))
        self._move_goal_marker()

    def _move_goal_marker(self):
        if self.set_entity_client is None:
            return
        if not self.set_entity_client.wait_for_service(timeout_sec=0.5):
            return
        try:
            req = self._SetEntityState.Request()
            req.state.name = S.GOAL_ENTITY_NAME
            req.state.pose.position.x = float(self.goal[0])
            req.state.pose.position.y = float(self.goal[1])
            req.state.pose.position.z = 0.0
            req.state.pose.orientation.w = 1.0
            self.set_entity_client.call_async(req)
        except Exception:  # noqa
            pass

    # ---------------- Interfaz tipo Gym ----------------
    def reset(self):
        self._stop_robot()
        self._call_reset()
        time.sleep(0.5)
        self._sample_goal()
        time.sleep(0.2)
        self.steps = 0
        self.prev_distance = self._distance_to_goal()
        return self._build_state()

    def step(self, exec_action):
        v, w = float(exec_action[0]), float(exec_action[1])
        self._publish_velocity(v, w)
        time.sleep(S.CONTROL_PERIOD)
        self.steps += 1

        state = self._build_state()
        dist = self._distance_to_goal()
        min_obs = float(self.scan_ranges.min())

        # ---- Reward shaping (criterio de evaluacion) ----
        reward = 0.0
        reward += S.K_PROGRESS * (self.prev_distance - dist)   # avance a la meta
        reward -= S.STEP_PENALTY                               # rapidez
        reward -= S.K_TURN * abs(w)                            # giros innecesarios
        if min_obs < S.OBSTACLE_NEAR:
            reward -= S.K_OBSTACLE * (S.OBSTACLE_NEAR - min_obs)
        self.prev_distance = dist

        done = False
        outcome = 'running'
        if dist < S.GOAL_REACHED_DIST:
            reward += S.SUCCESS_REWARD
            done, outcome = True, 'success'
        elif min_obs < S.COLLISION_DIST:
            reward += S.COLLISION_REWARD
            done, outcome = True, 'collision'
        elif self.steps >= S.MAX_STEPS:
            done, outcome = True, 'timeout'

        if done:
            self._stop_robot()
        return state, reward, done, {'outcome': outcome, 'distance': dist}