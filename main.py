import pygame
import math
import random
import heapq

pygame.init()

# ============================================================
# WINDOW
# ============================================================

WIDTH = 1200
HEIGHT = 750
HUD_HEIGHT = 170

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Autonomous Lunar Excavation Rover Simulator")

clock = pygame.time.Clock()

font = pygame.font.Font(None, 27)
small_font = pygame.font.Font(None, 21)
tiny_font = pygame.font.Font(None, 18)
title_font = pygame.font.Font(None, 35)


# ============================================================
# COLORS
# ============================================================

BLACK = (5, 5, 10)

MOON = (100, 100, 105)
MOON_LIGHT = (130, 130, 135)
MOON_DARK = (65, 65, 70)

WHITE = (240, 240, 240)
GREEN = (0, 230, 140)
BLUE = (0, 190, 255)
RED = (235, 70, 70)
ORANGE = (255, 170, 40)
YELLOW = (255, 220, 80)

ROCK = (60, 60, 65)
ROCK_LIGHT = (100, 100, 105)

ROVER_BODY = (185, 190, 195)
ROVER_DARK = (55, 65, 75)
WHEEL = (20, 20, 25)

REGOLITH = (160, 140, 105)
BERM = (185, 145, 75)


# ============================================================
# WORLD
# ============================================================

WORLD_WIDTH = 5000
WORLD_HEIGHT = 3500

GRID_SIZE = 70


# ============================================================
# ROVER
# ============================================================

rover_x = 500.0
rover_y = 1700.0

rover_angle = 0.0

ROVER_RADIUS = 32

manual_velocity = 0.0

MAX_SPEED = 4.0
AUTO_SPEED = 3.0

ACCELERATION = 0.12
FRICTION = 0.94

TURN_SPEED = 2.5

sensor_radius = 220

autonomous_mode = False

collector_spinning = False
collector_angle = 0

regolith_amount = 0.0

battery = 100.0

completed_trips = 0


# ============================================================
# MISSION STATES
# ============================================================

MISSION_MANUAL = "MANUAL CONTROL"

MISSION_TO_REGOLITH = "NAVIGATING TO REGOLITH"

MISSION_DIGGING = "EXCAVATING REGOLITH"

MISSION_TO_BERM = "TRANSPORTING REGOLITH"

MISSION_DUMPING = "BUILDING BERM"

mission_state = MISSION_MANUAL


# ============================================================
# TARGET LOCATIONS
# ============================================================

regolith_position = pygame.Vector2(
    4200,
    700
)

regolith_radius = 180


berm_position = pygame.Vector2(
    650,
    650
)

berm_radius = 120

berm_size = 35


# ============================================================
# LUNAR SURFACE TEXTURE
# ============================================================

surface_dots = []


# ============================================================
# CRATERS
# ============================================================

craters = []


# ============================================================
# ROCKS
# ============================================================

rocks = []

mission_notice = "NEW LUNAR MISSION GENERATED"
mission_notice_timer = 0

sensor_target = None


# ============================================================
# DUST PARTICLES
# ============================================================

dust_particles = []


# ============================================================
# A* VARIABLES
# ============================================================

current_path = []

current_waypoint = 0

current_target_name = None

replan_timer = 0


# ============================================================
# HELPERS
# ============================================================

def distance(x1, y1, x2, y2):

    return math.hypot(
        x2 - x1,
        y2 - y1
    )


def normalize_angle(angle):

    while angle > 180:
        angle -= 360

    while angle < -180:
        angle += 360

    return angle


# ============================================================
# COLLISION CHECK
# ============================================================

def position_is_safe(x, y):

    # World boundaries

    if x < ROVER_RADIUS + 20:
        return False

    if x > WORLD_WIDTH - ROVER_RADIUS - 20:
        return False

    if y < ROVER_RADIUS + 20:
        return False

    if y > WORLD_HEIGHT - ROVER_RADIUS - 20:
        return False


    # Craters

    for crater_x, crater_y, crater_radius in craters:

        safe_distance = (
            crater_radius
            + ROVER_RADIUS
            + 25
        )

        if distance(
            x,
            y,
            crater_x,
            crater_y
        ) < safe_distance:

            return False


    # Large rocks

    for rock_x, rock_y, rock_radius in rocks:

        safe_distance = (
            rock_radius
            + ROVER_RADIUS
            + 25
        )

        if distance(
            x,
            y,
            rock_x,
            rock_y
        ) < safe_distance:

            return False


    return True


# ============================================================
# SENSOR
# ============================================================

def nearest_hazard():

    global sensor_target

    nearest_type = "CLEAR"

    nearest_distance = sensor_radius + 1
    sensor_target = None


    # Craters

    for crater_x, crater_y, radius in craters:

        d = (
            distance(
                rover_x,
                rover_y,
                crater_x,
                crater_y
            )
            - radius
        )

        if (
            d <= sensor_radius
            and d < nearest_distance
        ):

            nearest_distance = d
            nearest_type = "CRATER"
            sensor_target = (crater_x, crater_y, radius)


    # Rocks

    for rock_x, rock_y, radius in rocks:

        d = (
            distance(
                rover_x,
                rover_y,
                rock_x,
                rock_y
            )
            - radius
        )

        if (
            d <= sensor_radius
            and d < nearest_distance
        ):

            nearest_distance = d

            if radius >= 22:

                nearest_type = "LARGE ROCK"

            else:

                nearest_type = "SMALL ROCK"

            sensor_target = (rock_x, rock_y, radius)


    if nearest_type == "CLEAR":

        return (
            "CLEAR",
            None
        )


    return (
        nearest_type,
        max(
            0,
            int(nearest_distance)
        )
    )


# ============================================================
# GRID CONVERSION
# ============================================================

def world_to_grid(x, y):

    return (
        int(x // GRID_SIZE),
        int(y // GRID_SIZE)
    )


def grid_to_world(grid_x, grid_y):

    return pygame.Vector2(
        grid_x * GRID_SIZE
        + GRID_SIZE / 2,

        grid_y * GRID_SIZE
        + GRID_SIZE / 2
    )


# ============================================================
# A* HELPERS
# ============================================================

def heuristic(a, b):

    return math.hypot(
        b[0] - a[0],
        b[1] - a[1]
    )


def grid_is_safe(grid_x, grid_y):

    max_x = WORLD_WIDTH // GRID_SIZE
    max_y = WORLD_HEIGHT // GRID_SIZE

    if not (0 <= grid_x < max_x and 0 <= grid_y < max_y):
        return False

    position = grid_to_world(
        grid_x,
        grid_y
    )

    return position_is_safe(
        position.x,
        position.y
    )


# ============================================================
# A* PATHFINDING
# ============================================================

def find_path(start_position, target_position, announce=True):

    start = world_to_grid(
        start_position.x,
        start_position.y
    )

    goal = world_to_grid(
        target_position.x,
        target_position.y
    )


    open_list = []

    heapq.heappush(
        open_list,
        (
            0,
            random.random(),
            start
        )
    )


    came_from = {}

    cost_so_far = {
        start: 0
    }


    directions = [

        (-1, 0),
        (1, 0),

        (0, -1),
        (0, 1),

        (-1, -1),
        (1, -1),

        (-1, 1),
        (1, 1)

    ]

    # Randomize equivalent choices so each valid mission can produce a
    # different route without using a manually authored route.
    random.shuffle(directions)


    max_x = (
        WORLD_WIDTH
        // GRID_SIZE
    )

    max_y = (
        WORLD_HEIGHT
        // GRID_SIZE
    )


    while open_list:

        _, _, current = heapq.heappop(
            open_list
        )


        if current == goal:
            break


        for dx, dy in directions:

            next_node = (
                current[0] + dx,
                current[1] + dy
            )


            # Stay inside world

            if not (
                0 <= next_node[0] < max_x
                and
                0 <= next_node[1] < max_y
            ):

                continue


            # Don't enter obstacles.

            if (
                not grid_is_safe(
                    next_node[0],
                    next_node[1]
                )
            ):

                continue


            # Diagonal movement costs more

            if (
                dx != 0
                and dy != 0
            ):

                # Prevent diagonal corner cutting through two blocked cells.
                if (
                    not grid_is_safe(
                        current[0] + dx,
                        current[1]
                    )
                    or not grid_is_safe(
                        current[0],
                        current[1] + dy
                    )
                ):

                    continue

                movement_cost = 1.414

            else:

                movement_cost = 1.0


            new_cost = (
                cost_so_far[current]
                + movement_cost
            )


            if (
                next_node
                not in cost_so_far
                or
                new_cost
                < cost_so_far[next_node]
            ):

                cost_so_far[
                    next_node
                ] = new_cost


                priority = (
                    new_cost
                    + heuristic(
                        next_node,
                        goal
                    )
                )


                heapq.heappush(
                    open_list,
                    (
                        priority,
                        random.random(),
                        next_node
                    )
                )


                came_from[
                    next_node
                ] = current


    # --------------------------------------------------------
    # NO PATH
    # --------------------------------------------------------

    if (
        goal not in came_from
        and goal != start
    ):

        if announce:
            print("WARNING: No safe path found.")

        return []


    # --------------------------------------------------------
    # REBUILD PATH
    # --------------------------------------------------------

    path = []

    current = goal


    while current != start:

        world_point = grid_to_world(
            current[0],
            current[1]
        )

        path.append(
            world_point
        )

        current = came_from[
            current
        ]


    path.reverse()


    # Final exact target

    path.append(
        pygame.Vector2(
            target_position.x,
            target_position.y
        )
    )


    return path


# ============================================================
# PROCEDURAL MISSION GENERATION
# ============================================================

def generate_new_mission():

    global rover_x
    global rover_y
    global rover_angle
    global regolith_amount
    global battery
    global completed_trips
    global berm_size
    global craters
    global rocks
    global surface_dots
    global mission_state
    global autonomous_mode
    global collector_spinning
    global mission_notice
    global mission_notice_timer
    global current_path
    global current_waypoint
    global current_target_name

    rover_x = 500.0
    rover_y = 1700.0
    rover_angle = 0.0
    regolith_amount = 0.0
    battery = 100.0
    completed_trips = 0
    berm_size = 35
    autonomous_mode = False
    collector_spinning = False
    mission_state = MISSION_MANUAL
    mission_notice = "NEW LUNAR MISSION GENERATED"
    mission_notice_timer = 240

    current_path = []
    current_waypoint = 0
    current_target_name = None

    protected_locations = [
        (rover_x, rover_y, 300),
        (regolith_position.x, regolith_position.y, regolith_radius + 130),
        (berm_position.x, berm_position.y, berm_radius + 100)
    ]

    def clear_of_mission_areas(x, y, radius):

        for protected_x, protected_y, protected_radius in protected_locations:

            if distance(x, y, protected_x, protected_y) < radius + protected_radius:
                return False

        return True

    for attempt in range(80):

        candidate_craters = []

        for crater_index in range(random.randint(8, 14)):

            crater_radius = random.randint(85, 210)
            crater_x = random.randint(250, WORLD_WIDTH - 250)
            crater_y = random.randint(250, WORLD_HEIGHT - 250)

            if clear_of_mission_areas(crater_x, crater_y, crater_radius + 30):
                candidate_craters.append((crater_x, crater_y, crater_radius))

        candidate_rocks = []

        for rock_index in range(random.randint(65, 105)):

            # Both small traversable rocks and large blocked rocks are generated.
            rock_radius = random.randint(10, 44)
            rock_x = random.randint(100, WORLD_WIDTH - 100)
            rock_y = random.randint(100, WORLD_HEIGHT - 100)

            if clear_of_mission_areas(rock_x, rock_y, rock_radius + 35):
                candidate_rocks.append((rock_x, rock_y, rock_radius))

        craters = candidate_craters
        rocks = candidate_rocks

        start = pygame.Vector2(rover_x, rover_y)
        to_regolith = find_path(start, regolith_position, announce=False)
        to_berm = find_path(regolith_position, berm_position, announce=False)

        if to_regolith and to_berm:
            surface_dots = [
                (
                    random.randint(0, WORLD_WIDTH),
                    random.randint(0, WORLD_HEIGHT),
                    random.randint(1, 3)
                )
                for dot_index in range(1800)
            ]
            print(f"NEW LUNAR MISSION GENERATED (attempt {attempt + 1})")
            print(f"Terrain: {len(candidate_craters)} craters, {len(candidate_rocks)} rocks")
            return

    # The fallback remains random but sparse, making a valid mission almost certain.
    craters = []
    rocks = []
    surface_dots = [
        (
            random.randint(0, WORLD_WIDTH),
            random.randint(0, WORLD_HEIGHT),
            random.randint(1, 3)
        )
        for dot_index in range(1800)
    ]
    print("WARNING: Sparse fallback terrain generated.")


# ============================================================
# PLAN NEW ROUTE
# ============================================================

def plan_route(target, target_name):

    global current_path
    global current_waypoint
    global current_target_name


    print(
        f"Planning A* route to {target_name}..."
    )


    current_path = find_path(

        pygame.Vector2(
            rover_x,
            rover_y
        ),

        target

    )


    current_waypoint = 0

    current_target_name = target_name


    print(
        f"Path contains {len(current_path)} waypoints."
    )

    if current_path:
        print("NEW PATH FOUND")


def route_is_blocked():

    for waypoint in current_path[current_waypoint:]:

        if not position_is_safe(waypoint.x, waypoint.y):
            return True

    return False


# ============================================================
# AUTONOMOUS DRIVE
# ============================================================

def autonomous_drive(
    target,
    target_name
):

    global rover_x
    global rover_y
    global rover_angle

    global current_path
    global current_waypoint
    global current_target_name

    global replan_timer


    # --------------------------------------------------------
    # PLAN PATH
    # --------------------------------------------------------

    if (
        not current_path
        or
        current_target_name
        != target_name
    ):

        plan_route(
            target,
            target_name
        )

    elif route_is_blocked():

        print("PATH BLOCKED")
        print("REPLANNING...")
        reset_path()
        plan_route(target, target_name)


    if not current_path:

        return False


    if (
        current_waypoint
        >= len(current_path)
    ):

        return True


    waypoint = current_path[
        current_waypoint
    ]


    # --------------------------------------------------------
    # WAYPOINT REACHED
    # --------------------------------------------------------

    waypoint_distance = distance(
        rover_x,
        rover_y,
        waypoint.x,
        waypoint.y
    )


    if waypoint_distance < 38:

        current_waypoint += 1


        if (
            current_waypoint
            >= len(current_path)
        ):

            return True


        waypoint = current_path[
            current_waypoint
        ]


    # --------------------------------------------------------
    # DESIRED HEADING
    # --------------------------------------------------------

    desired_angle = math.degrees(

        math.atan2(

            waypoint.y
            - rover_y,

            waypoint.x
            - rover_x

        )

    )


    angle_difference = normalize_angle(
        desired_angle
        - rover_angle
    )


    # --------------------------------------------------------
    # STEER
    # --------------------------------------------------------

    if angle_difference > 1:

        rover_angle += min(
            TURN_SPEED,
            angle_difference
        )


    elif angle_difference < -1:

        rover_angle -= min(
            TURN_SPEED,
            abs(angle_difference)
        )


    rover_angle %= 360


    # --------------------------------------------------------
    # SPEED BASED ON TURN
    # --------------------------------------------------------

    if abs(angle_difference) < 15:

        speed = AUTO_SPEED

    elif abs(angle_difference) < 45:

        speed = 1.8

    else:

        speed = 0.7


    radians = math.radians(
        rover_angle
    )


    new_x = (
        rover_x
        + math.cos(radians)
        * speed
    )

    new_y = (
        rover_y
        + math.sin(radians)
        * speed
    )


    # --------------------------------------------------------
    # COLLISION CHECK
    # --------------------------------------------------------

    if position_is_safe(
        new_x,
        new_y
    ):

        rover_x = new_x
        rover_y = new_y

        replan_timer = 0


    else:

        replan_timer += 1


        # Something blocked the route.
        # Calculate another path.

        if replan_timer > 10:

            print("PATH BLOCKED")
            print("REPLANNING...")

            current_path = []

            current_waypoint = 0

            replan_timer = 0

            plan_route(target, target_name)


    # --------------------------------------------------------
    # TARGET REACHED?
    # --------------------------------------------------------

    target_distance = distance(
        rover_x,
        rover_y,
        target.x,
        target.y
    )


    return target_distance < 80


# ============================================================
# MANUAL DRIVE
# ============================================================

def manual_drive():

    global rover_x
    global rover_y
    global rover_angle
    global manual_velocity


    keys = pygame.key.get_pressed()


    # --------------------------------------------------------
    # ACCELERATE
    # --------------------------------------------------------

    if (
        keys[pygame.K_w]
        or keys[pygame.K_UP]
    ):

        manual_velocity += ACCELERATION


    elif (
        keys[pygame.K_s]
        or keys[pygame.K_DOWN]
    ):

        manual_velocity -= ACCELERATION


    else:

        manual_velocity *= FRICTION


    manual_velocity = max(
        -MAX_SPEED * 0.55,
        min(
            MAX_SPEED,
            manual_velocity
        )
    )


    # --------------------------------------------------------
    # STEERING
    # --------------------------------------------------------

    steering_factor = max(
        0.35,
        abs(manual_velocity)
        / MAX_SPEED
    )


    if (
        keys[pygame.K_a]
        or keys[pygame.K_LEFT]
    ):

        rover_angle -= (
            TURN_SPEED
            * steering_factor
        )


    if (
        keys[pygame.K_d]
        or keys[pygame.K_RIGHT]
    ):

        rover_angle += (
            TURN_SPEED
            * steering_factor
        )


    rover_angle %= 360


    # --------------------------------------------------------
    # MOVE
    # --------------------------------------------------------

    radians = math.radians(
        rover_angle
    )


    new_x = (
        rover_x
        + math.cos(radians)
        * manual_velocity
    )

    new_y = (
        rover_y
        + math.sin(radians)
        * manual_velocity
    )


    if position_is_safe(
        new_x,
        new_y
    ):

        rover_x = new_x
        rover_y = new_y

    else:

        manual_velocity *= -0.15


# ============================================================
# CAMERA
# ============================================================

def get_camera():

    camera_x = (
        rover_x
        - WIDTH / 2
    )

    camera_y = (
        rover_y
        - (HEIGHT + HUD_HEIGHT) / 2
    )


    camera_x = max(
        0,
        min(
            WORLD_WIDTH - WIDTH,
            camera_x
        )
    )


    camera_y = max(
        0,
        min(
            WORLD_HEIGHT - (HEIGHT - HUD_HEIGHT),
            camera_y
        )
    )


    return (
        camera_x,
        camera_y
    )


# ============================================================
# DRAW WORLD
# ============================================================

def draw_world(
    camera_x,
    camera_y
):

    screen.fill(
        MOON
    )


    # --------------------------------------------------------
    # SURFACE TEXTURE
    # --------------------------------------------------------

    for x, y, size in surface_dots:

        screen_x = (
            x - camera_x
        )

        screen_y = (
            y - camera_y
        )


        if (
            -5 <= screen_x <= WIDTH + 5
            and
            -5 <= screen_y <= HEIGHT + 5
        ):

            pygame.draw.circle(
                screen,
                MOON_LIGHT,
                (
                    int(screen_x),
                    int(screen_y)
                ),
                size
            )


# ============================================================
# DRAW CRATERS
# ============================================================

def draw_craters(
    camera_x,
    camera_y
):

    for x, y, radius in craters:

        screen_x = int(
            x - camera_x
        )

        screen_y = int(
            y - camera_y
        )


        pygame.draw.circle(
            screen,
            MOON_LIGHT,
            (
                screen_x,
                screen_y
            ),
            radius
        )


        pygame.draw.circle(
            screen,
            MOON_DARK,
            (
                screen_x,
                screen_y
            ),
            radius - 10
        )


        pygame.draw.circle(
            screen,
            (45, 45, 50),
            (
                screen_x + 12,
                screen_y + 12
            ),
            max(
                5,
                radius - 30
            )
        )


# ============================================================
# DRAW ROCKS
# ============================================================

def draw_rocks(
    camera_x,
    camera_y
):

    for x, y, radius in rocks:

        screen_x = int(
            x - camera_x
        )

        screen_y = int(
            y - camera_y
        )


        pygame.draw.circle(
            screen,
            ROCK,
            (
                screen_x,
                screen_y
            ),
            radius
        )


        pygame.draw.circle(
            screen,
            ROCK_LIGHT,
            (
                screen_x
                - radius // 3,

                screen_y
                - radius // 3
            ),
            max(
                3,
                radius // 3
            )
        )


# ============================================================
# DRAW REGOLITH FIELD
# ============================================================

def draw_regolith(
    camera_x,
    camera_y
):

    x = int(
        regolith_position.x
        - camera_x
    )

    y = int(
        regolith_position.y
        - camera_y
    )


    pygame.draw.circle(
        screen,
        REGOLITH,
        (
            x,
            y
        ),
        regolith_radius
    )


    pygame.draw.circle(
        screen,
        ORANGE,
        (
            x,
            y
        ),
        regolith_radius,
        4
    )


    label = font.render(
        "REGOLITH FIELD",
        True,
        WHITE
    )


    screen.blit(
        label,
        (
            x - 75,
            y - 15
        )
    )


# ============================================================
# DRAW BERM
# ============================================================

def draw_berm(
    camera_x,
    camera_y
):

    x = int(
        berm_position.x
        - camera_x
    )

    y = int(
        berm_position.y
        - camera_y
    )


    pygame.draw.circle(
        screen,
        BERM,
        (
            x,
            y
        ),
        int(berm_size)
    )


    pygame.draw.circle(
        screen,
        YELLOW,
        (
            x,
            y
        ),
        int(berm_size),
        3
    )

    # Each completed load adds a visible raised layer to the berm.
    for layer in range(3):

        layer_radius = max(8, int(berm_size) - layer * 9)
        pygame.draw.arc(
            screen,
            (210, 170, 95),
            (
                x - layer_radius,
                y - layer_radius,
                layer_radius * 2,
                layer_radius * 2
            ),
            math.radians(15),
            math.radians(205),
            3
        )


    label = font.render(
        f"BERM  DEPOSITED: {int(berm_size)}",
        True,
        WHITE
    )


    screen.blit(
        label,
        (
            x - 80,
            y - 12
        )
    )


# ============================================================
# DRAW A* PATH
# ============================================================

def draw_path(
    camera_x,
    camera_y
):

    if not autonomous_mode:
        return


    if not current_path:
        return


    if (
        current_waypoint
        >= len(current_path)
    ):

        return


    points = [

        (
            int(
                rover_x
                - camera_x
            ),

            int(
                rover_y
                - camera_y
            )
        )

    ]


    for waypoint in current_path[
        current_waypoint:
    ]:

        points.append(
            (
                int(
                    waypoint.x
                    - camera_x
                ),

                int(
                    waypoint.y
                    - camera_y
                )
            )
        )


    if len(points) >= 2:

        pygame.draw.lines(
            screen,
            BLUE,
            False,
            points,
            3
        )


    for point in points[1:]:

        pygame.draw.circle(
            screen,
            BLUE,
            point,
            4
        )


# ============================================================
# DUST
# ============================================================

def create_dust(
    x,
    y,
    amount=2
):

    for i in range(amount):

        dust_particles.append(
            [
                x + random.uniform(
                    -25,
                    25
                ),

                y + random.uniform(
                    -25,
                    25
                ),

                random.uniform(
                    -1.2,
                    1.2
                ),

                random.uniform(
                    -1.2,
                    1.2
                ),

                random.randint(
                    20,
                    50
                )
            ]
        )


def update_and_draw_dust(
    camera_x,
    camera_y
):

    for particle in dust_particles[:]:

        particle[0] += particle[2]

        particle[1] += particle[3]

        particle[4] -= 1


        if particle[4] <= 0:

            dust_particles.remove(
                particle
            )

            continue


        pygame.draw.circle(
            screen,
            REGOLITH,
            (
                int(
                    particle[0]
                    - camera_x
                ),

                int(
                    particle[1]
                    - camera_y
                )
            ),
            3
        )


# ============================================================
# DRAW ROVER
# ============================================================

def draw_sensor_detection(camera_x, camera_y):

    hazard, hazard_distance = nearest_hazard()

    if hazard == "CLEAR" or sensor_target is None:
        return

    target_x, target_y, target_radius = sensor_target
    rover_screen = (int(rover_x - camera_x), int(rover_y - camera_y))
    target_screen = (int(target_x - camera_x), int(target_y - camera_y))

    pygame.draw.line(
        screen,
        RED,
        rover_screen,
        target_screen,
        2
    )

    pygame.draw.circle(
        screen,
        RED,
        target_screen,
        target_radius + 9,
        3
    )

def draw_rover(
    camera_x,
    camera_y
):

    # Rover is drawn on its own transparent surface,
    # then rotated according to rover heading.

    rover_surface = pygame.Surface(
        (
            120,
            90
        ),
        pygame.SRCALPHA
    )


    center_x = 60
    center_y = 45


    # --------------------------------------------------------
    # WHEELS
    # --------------------------------------------------------

    wheel_locations = [

        (22, 15),
        (22, 35),
        (22, 55),

        (82, 15),
        (82, 35),
        (82, 55)

    ]


    for wheel_x, wheel_y in wheel_locations:

        pygame.draw.rect(
            rover_surface,
            WHEEL,
            (
                wheel_x,
                wheel_y,
                17,
                20
            ),
            border_radius=4
        )


    # --------------------------------------------------------
    # BODY
    # --------------------------------------------------------

    pygame.draw.rect(
        rover_surface,
        ROVER_BODY,
        (
            35,
            18,
            50,
            55
        ),
        border_radius=10
    )


    pygame.draw.rect(
        rover_surface,
        ROVER_DARK,
        (
            44,
            29,
            32,
            30
        ),
        border_radius=6
    )


    # --------------------------------------------------------
    # SENSOR
    # --------------------------------------------------------

    pygame.draw.circle(
        rover_surface,
        BLUE,
        (
            64,
            43
        ),
        7
    )


    # --------------------------------------------------------
    # STORAGE
    # --------------------------------------------------------

    pygame.draw.rect(
        rover_surface,
        (90, 100, 110),
        (
            48,
            52,
            25,
            15
        )
    )


    if regolith_amount > 0:

        fill_width = int(
            21
            * regolith_amount
            / 100
        )


        pygame.draw.rect(
            rover_surface,
            REGOLITH,
            (
                50,
                54,
                fill_width,
                11
            )
        )


    # --------------------------------------------------------
    # EXCAVATOR
    # --------------------------------------------------------

    pygame.draw.line(
        rover_surface,
        ROVER_BODY,
        (
            85,
            30
        ),
        (
            103,
            30
        ),
        4
    )


    pygame.draw.line(
        rover_surface,
        ROVER_BODY,
        (
            85,
            60
        ),
        (
            103,
            60
        ),
        4
    )


    pygame.draw.circle(
        rover_surface,
        ORANGE,
        (
            105,
            45
        ),
        15,
        3
    )


    for blade in range(6):

        angle = math.radians(
            collector_angle
            + blade * 60
        )


        end_x = int(
            105
            + math.cos(angle)
            * 12
        )

        end_y = int(
            45
            + math.sin(angle)
            * 12
        )


        pygame.draw.line(
            rover_surface,
            ORANGE,
            (
                105,
                45
            ),
            (
                end_x,
                end_y
            ),
            3
        )


    # --------------------------------------------------------
    # ROTATE ROVER
    # --------------------------------------------------------

    draw_sensor_detection(camera_x, camera_y)

    rotated = pygame.transform.rotate(
        rover_surface,
        -rover_angle
    )


    rect = rotated.get_rect(
        center=(
            int(
                rover_x
                - camera_x
            ),

            int(
                rover_y
                - camera_y
            )
        )
    )


    screen.blit(
        rotated,
        rect
    )


    # --------------------------------------------------------
    # SENSOR RANGE
    # --------------------------------------------------------

    pygame.draw.circle(
        screen,
        BLUE,
        (
            int(
                rover_x
                - camera_x
            ),

            int(
                rover_y
                - camera_y
            )
        ),
        sensor_radius,
        2
    )


# ============================================================
# MINIMAP
# ============================================================

def draw_minimap():

    map_width = 250
    map_height = 175

    map_x = WIDTH - map_width - 20
    map_y = HUD_HEIGHT + 15


    pygame.draw.rect(
        screen,
        (20, 22, 27),
        (
            map_x,
            map_y,
            map_width,
            map_height
        ),
        border_radius=8
    )


    pygame.draw.rect(
        screen,
        WHITE,
        (
            map_x,
            map_y,
            map_width,
            map_height
        ),
        2,
        border_radius=8
    )


    scale_x = (
        map_width
        / WORLD_WIDTH
    )

    scale_y = (
        map_height
        / WORLD_HEIGHT
    )


    # --------------------------------------------------------
    # CRATERS
    # --------------------------------------------------------

    for x, y, radius in craters:

        pygame.draw.circle(
            screen,
            MOON_DARK,
            (
                int(
                    map_x
                    + x * scale_x
                ),

                int(
                    map_y
                    + y * scale_y
                )
            ),
            max(
                2,
                int(
                    radius
                    * scale_x
                )
            )
        )


    # --------------------------------------------------------
    # LARGE ROCKS
    # --------------------------------------------------------

    for x, y, radius in rocks:

        if radius < 22:
            continue


        pygame.draw.circle(
            screen,
            ROCK_LIGHT,
            (
                int(
                    map_x
                    + x * scale_x
                ),

                int(
                    map_y
                    + y * scale_y
                )
            ),
            2
        )


    # --------------------------------------------------------
    # PATH
    # --------------------------------------------------------

    if (
        autonomous_mode
        and current_path
        and current_waypoint
        < len(current_path)
    ):

        mini_path = []


        mini_path.append(
            (
                int(
                    map_x
                    + rover_x
                    * scale_x
                ),

                int(
                    map_y
                    + rover_y
                    * scale_y
                )
            )
        )


        for waypoint in current_path[
            current_waypoint:
        ]:

            mini_path.append(
                (
                    int(
                        map_x
                        + waypoint.x
                        * scale_x
                    ),

                    int(
                        map_y
                        + waypoint.y
                        * scale_y
                    )
                )
            )


        if len(mini_path) >= 2:

            pygame.draw.lines(
                screen,
                BLUE,
                False,
                mini_path,
                2
            )


    # --------------------------------------------------------
    # REGOLITH
    # --------------------------------------------------------

    pygame.draw.circle(
        screen,
        ORANGE,
        (
            int(
                map_x
                + regolith_position.x
                * scale_x
            ),

            int(
                map_y
                + regolith_position.y
                * scale_y
            )
        ),
        6
    )


    # --------------------------------------------------------
    # BERM
    # --------------------------------------------------------

    pygame.draw.circle(
        screen,
        YELLOW,
        (
            int(
                map_x
                + berm_position.x
                * scale_x
            ),

            int(
                map_y
                + berm_position.y
                * scale_y
            )
        ),
        6
    )


    # --------------------------------------------------------
    # ROVER
    # --------------------------------------------------------

    pygame.draw.circle(
        screen,
        GREEN,
        (
            int(
                map_x
                + rover_x
                * scale_x
            ),

            int(
                map_y
                + rover_y
                * scale_y
            )
        ),
        5
    )


    label = tiny_font.render(
        "LUNAR NAVIGATION MAP",
        True,
        WHITE
    )


    screen.blit(
        label,
        (
            map_x + 8,
            map_y + 7
        )
    )


# ============================================================
# HUD
# ============================================================

def draw_legacy_hud():

    pygame.draw.rect(
        screen,
        (18, 20, 25),
        (
            0,
            0,
            WIDTH,
            105
        )
    )


    title = title_font.render(
        "AUTONOMOUS LUNAR EXCAVATION ROVER",
        True,
        WHITE
    )


    screen.blit(
        title,
        (
            18,
            10
        )
    )


    # --------------------------------------------------------
    # MODE
    # --------------------------------------------------------

    if autonomous_mode:

        mode = "AUTO"
        mode_color = GREEN

    else:

        mode = "MANUAL"
        mode_color = WHITE


    mode_display = font.render(
        f"MODE: {mode}",
        True,
        mode_color
    )


    screen.blit(
        mode_display,
        (
            520,
            13
        )
    )


    # --------------------------------------------------------
    # REGOLITH
    # --------------------------------------------------------

    storage_display = font.render(
        f"REGOLITH: {int(regolith_amount)}%",
        True,
        ORANGE
    )


    screen.blit(
        storage_display,
        (
            665,
            13
        )
    )


    # --------------------------------------------------------
    # BATTERY
    # --------------------------------------------------------

    battery_color = (
        GREEN
        if battery > 25
        else RED
    )


    battery_display = font.render(
        f"BATTERY: {int(battery)}%",
        True,
        battery_color
    )


    screen.blit(
        battery_display,
        (
            855,
            13
        )
    )


    # --------------------------------------------------------
    # SENSOR
    # --------------------------------------------------------

    hazard, hazard_distance = (
        nearest_hazard()
    )


    if hazard == "CLEAR":

        sensor_string = (
            "SENSOR: CLEAR"
        )

        sensor_color = GREEN

    else:

        sensor_string = (
            f"SENSOR: {hazard} "
            f"DISTANCE: {hazard_distance}px"
        )

        sensor_color = RED


    sensor_display = small_font.render(
        sensor_string,
        True,
        sensor_color
    )


    screen.blit(
        sensor_display,
        (
            1010,
            17
        )
    )


    # --------------------------------------------------------
    # MISSION
    # --------------------------------------------------------

    mission_display = small_font.render(
        f"MISSION: {mission_state}",
        True,
        GREEN
        if autonomous_mode
        else WHITE
    )


    screen.blit(
        mission_display,
        (
            18,
            52
        )
    )

    navigation_display = small_font.render(
        f"NAVIGATION: A*   PATH: {'ACTIVE' if current_path else 'WAITING'}",
        True,
        BLUE if current_path else WHITE
    )

    screen.blit(
        navigation_display,
        (18, 78)
    )

    if current_path:
        waypoint_display = tiny_font.render(
            f"WAYPOINT: {min(current_waypoint + 1, len(current_path))} / {len(current_path)}",
            True,
            BLUE
        )
        screen.blit(waypoint_display, (390, 80))

    if mission_notice_timer > 0:
        notice_display = small_font.render(
            mission_notice,
            True,
            YELLOW
        )
        screen.blit(
            notice_display,
            notice_display.get_rect(center=(WIDTH // 2, 96))
        )


    # --------------------------------------------------------
    # TRIPS
    # --------------------------------------------------------

    trip_display = small_font.render(
        f"BERM LOADS: {completed_trips}",
        True,
        YELLOW
    )


    screen.blit(
        trip_display,
        (
            390,
            52
        )
    )


    # --------------------------------------------------------
    # CONTROLS
    # --------------------------------------------------------

    controls = small_font.render(
        "W/S Drive   A/D Steer   M Auto/Manual   R New Mission   SPACE Collector",
        True,
        WHITE
    )


    screen.blit(
        controls,
        (
            570,
            52
        )
    )


# ============================================================
# ENGINEERING TELEMETRY DASHBOARD
# ============================================================

def draw_hud():

    dashboard_background = (16, 19, 24)
    panel_background = (23, 27, 34)
    divider = (70, 78, 88)
    muted = (170, 178, 188)

    pygame.draw.rect(
        screen,
        dashboard_background,
        (0, 0, WIDTH, HUD_HEIGHT)
    )

    pygame.draw.line(
        screen,
        (95, 105, 115),
        (0, HUD_HEIGHT - 1),
        (WIDTH, HUD_HEIGHT - 1),
        1
    )

    title = title_font.render(
        "AUTONOMOUS LUNAR EXCAVATION ROVER",
        True,
        WHITE
    )
    screen.blit(title, (24, 12))

    mode = "AUTO" if autonomous_mode else "MANUAL"
    mode_color = GREEN if autonomous_mode else muted
    mode_display = font.render(mode, True, mode_color)
    mode_x = WIDTH - mode_display.get_width() - 30

    pygame.draw.circle(
        screen,
        mode_color,
        (mode_x - 14, 28),
        5
    )
    screen.blit(mode_display, (mode_x, 15))

    mission_label = tiny_font.render("MISSION", True, muted)
    mission_display = font.render(mission_state, True, WHITE)
    screen.blit(mission_label, (24, 53))
    screen.blit(mission_display, (24, 69))

    if mission_notice_timer > 0:
        notice_display = tiny_font.render(
            mission_notice,
            True,
            YELLOW
        )
        screen.blit(
            notice_display,
            (
                WIDTH - notice_display.get_width() - 24,
                75
            )
        )

    pygame.draw.line(
        screen,
        divider,
        (24, 98),
        (WIDTH - 24, 98),
        1
    )

    panel_rectangles = [
        (24, 104, 335, 43),
        (385, 104, 350, 43),
        (761, 104, 415, 43)
    ]

    for panel_rectangle in panel_rectangles:
        pygame.draw.rect(
            screen,
            panel_background,
            panel_rectangle,
            border_radius=3
        )

    pygame.draw.line(
        screen,
        divider,
        (373, 104),
        (373, 147),
        1
    )
    pygame.draw.line(
        screen,
        divider,
        (749, 104),
        (749, 147),
        1
    )

    navigation_label = tiny_font.render("NAVIGATION", True, muted)
    screen.blit(navigation_label, (36, 107))

    if not autonomous_mode:
        path_status = "STANDBY"
    elif replan_timer > 0:
        path_status = "REPLANNING"
    elif current_path and current_waypoint < len(current_path):
        path_status = "ACTIVE"
    elif current_target_name:
        path_status = "COMPLETE"
    else:
        path_status = "WAITING"

    path_display = small_font.render(
        f"A* Path: {path_status}",
        True,
        BLUE if path_status in ("ACTIVE", "REPLANNING") else WHITE
    )
    screen.blit(path_display, (36, 124))

    waypoint_total = len(current_path)
    waypoint_number = min(current_waypoint + 1, waypoint_total)
    waypoint_display = tiny_font.render(
        f"Waypoint: {waypoint_number}/{waypoint_total}",
        True,
        BLUE
    )
    screen.blit(waypoint_display, (216, 128))

    status_label = tiny_font.render("ROVER STATUS", True, muted)
    screen.blit(status_label, (397, 107))

    battery_color = GREEN if battery > 25 else RED
    battery_display = small_font.render(
        f"Battery: {int(battery)}%",
        True,
        battery_color
    )
    screen.blit(battery_display, (397, 124))

    hazard, hazard_distance = nearest_hazard()

    if hazard == "CLEAR":
        sensor_display = small_font.render(
            "Sensor: CLEAR",
            True,
            GREEN
        )
        sensor_detail = tiny_font.render(
            "No hazards detected",
            True,
            muted
        )
    else:
        sensor_display = small_font.render(
            "Sensor: HAZARD",
            True,
            RED
        )
        sensor_detail = tiny_font.render(
            f"{hazard}  |  {hazard_distance}px",
            True,
            RED
        )

    screen.blit(sensor_display, (555, 124))
    screen.blit(sensor_detail, (555, 141))

    progress_label = tiny_font.render("MISSION PROGRESS", True, muted)
    screen.blit(progress_label, (773, 107))

    regolith_display = small_font.render(
        f"Regolith: {int(regolith_amount)}%",
        True,
        ORANGE
    )
    loads_display = small_font.render(
        f"Berm Loads: {completed_trips}",
        True,
        YELLOW
    )
    screen.blit(regolith_display, (773, 124))
    screen.blit(loads_display, (1000, 124))

    pygame.draw.rect(
        screen,
        (55, 60, 68),
        (773, 142, 180, 5),
        border_radius=2
    )
    pygame.draw.rect(
        screen,
        ORANGE,
        (773, 142, int(180 * regolith_amount / 100), 5),
        border_radius=2
    )

    pygame.draw.line(
        screen,
        divider,
        (24, 150),
        (WIDTH - 24, 150),
        1
    )

    footer_font = pygame.font.Font(None, 16)
    controls = footer_font.render(
        "W/S Drive   |   A/D Steer   |   M Auto/Manual   |   R New Mission   |   SPACE Collector",
        True,
        muted
    )
    screen.blit(controls, (24, 152))


# ============================================================
# RESET PATH
# ============================================================

def reset_path():

    global current_path
    global current_waypoint
    global current_target_name

    current_path = []

    current_waypoint = 0

    current_target_name = None


# Build the first random world only after all A* functions exist.
generate_new_mission()


# ============================================================
# MAIN PROGRAM
# ============================================================

running = True


while running:

    # --------------------------------------------------------
    # EVENTS
    # --------------------------------------------------------

    for event in pygame.event.get():

        if event.type == pygame.QUIT:

            running = False


        if event.type == pygame.KEYDOWN:

            # Generate a new terrain and stop the current mission.
            if event.key == pygame.K_r:

                generate_new_mission()
                manual_velocity = 0

                print("Press M to start the new autonomous mission.")

            # ------------------------------------------------
            # AUTO / MANUAL
            # ------------------------------------------------

            if event.key == pygame.K_m:

                autonomous_mode = (
                    not autonomous_mode
                )

                reset_path()

                manual_velocity = 0


                if autonomous_mode:

                    mission_state = (
                        MISSION_TO_REGOLITH
                    )

                    collector_spinning = False

                    print(
                        "AUTO MODE ENABLED"
                    )


                else:

                    mission_state = (
                        MISSION_MANUAL
                    )

                    collector_spinning = False

                    print(
                        "MANUAL MODE ENABLED"
                    )


            # ------------------------------------------------
            # MANUAL COLLECTOR
            # ------------------------------------------------

            if (
                event.key
                == pygame.K_SPACE
                and not autonomous_mode
            ):

                collector_spinning = (
                    not collector_spinning
                )


    # ========================================================
    # AUTO MISSION
    # ========================================================

    if mission_notice_timer > 0:
        mission_notice_timer -= 1

    if autonomous_mode:

        manual_velocity = 0


        # ----------------------------------------------------
        # NAVIGATE TO REGOLITH
        # ----------------------------------------------------

        if (
            mission_state
            == MISSION_TO_REGOLITH
        ):

            collector_spinning = False


            reached = autonomous_drive(
                regolith_position,
                "REGOLITH"
            )


            if (
                reached
                or distance(
                    rover_x,
                    rover_y,
                    regolith_position.x,
                    regolith_position.y
                ) < 100
            ):

                mission_state = (
                    MISSION_DIGGING
                )

                collector_spinning = True

                reset_path()


        # ----------------------------------------------------
        # DIG
        # ----------------------------------------------------

        elif (
            mission_state
            == MISSION_DIGGING
        ):

            collector_spinning = True


            regolith_amount += 0.12


            create_dust(
                rover_x,
                rover_y,
                2
            )


            if regolith_amount >= 100:

                regolith_amount = 100

                collector_spinning = False

                mission_state = (
                    MISSION_TO_BERM
                )

                reset_path()


        # ----------------------------------------------------
        # TRANSPORT TO BERM
        # ----------------------------------------------------

        elif (
            mission_state
            == MISSION_TO_BERM
        ):

            collector_spinning = False


            reached = autonomous_drive(
                berm_position,
                "BERM"
            )


            if (
                reached
                or distance(
                    rover_x,
                    rover_y,
                    berm_position.x,
                    berm_position.y
                ) < 90
            ):

                mission_state = (
                    MISSION_DUMPING
                )

                reset_path()


        # ----------------------------------------------------
        # DUMP
        # ----------------------------------------------------

        elif (
            mission_state
            == MISSION_DUMPING
        ):

            regolith_amount -= 0.35


            create_dust(
                rover_x,
                rover_y,
                3
            )


            if regolith_amount <= 0:

                regolith_amount = 0

                completed_trips += 1

                berm_size = min(
                    berm_radius - 10,
                    berm_size + 8
                )

                mission_state = (
                    MISSION_TO_REGOLITH
                )

                reset_path()


    # ========================================================
    # MANUAL MODE
    # ========================================================

    else:

        manual_drive()


    # ========================================================
    # COLLECTOR ROTATION
    # ========================================================

    if collector_spinning:

        collector_angle += 9

        collector_angle %= 360


    # ========================================================
    # BATTERY
    # ========================================================

    if autonomous_mode:

        battery -= 0.0008

    elif abs(manual_velocity) > 0.1:

        battery -= 0.0005


    battery = max(
        0,
        battery
    )


    # ========================================================
    # CAMERA
    # ========================================================

    camera_x, camera_y = (
        get_camera()
    )


    # ========================================================
    # DRAW
    # ========================================================

    draw_world(
        camera_x,
        camera_y
    )


    draw_regolith(
        camera_x,
        camera_y
    )


    draw_berm(
        camera_x,
        camera_y
    )


    draw_craters(
        camera_x,
        camera_y
    )


    draw_rocks(
        camera_x,
        camera_y
    )


    # Draw A* route underneath rover

    draw_path(
        camera_x,
        camera_y
    )


    update_and_draw_dust(
        camera_x,
        camera_y
    )


    draw_rover(
        camera_x,
        camera_y
    )


    draw_hud()

    draw_minimap()


    # ========================================================
    # UPDATE SCREEN
    # ========================================================

    pygame.display.flip()

    clock.tick(60)


pygame.quit()