import random

WIDTH = 40
HEIGHT = 20
INITIAL_SNAKE_LENGTH = 3
SNAKE_BODY_SYMBOL = '■'
SNAKE_HEAD_SYMBOL = '⬢' # to denote the head i m using this symbol
FOOD_SYMBOL = '●'

class Snake:
    def __init__(self, player_id, x, y):
        self.id = player_id
        self.body = [(y, x - i) for i in range(INITIAL_SNAKE_LENGTH)]
        self.direction = 'RIGHT'
        self.is_alive = True
        self.score = 0

    def to_dict(self):
        """Serializes the snake's state into a dictionary for JSON."""
        return {
            'body': self.body,
            'is_alive': self.is_alive,
            'score': self.score
        }

    def move(self):
        """Moves the snake one step in its current direction."""
        if not self.is_alive: return
        head_y, head_x = self.body[0]

        if self.direction == 'UP': new_head = (head_y - 1, head_x)
        elif self.direction == 'DOWN': new_head = (head_y + 1, head_x)
        elif self.direction == 'LEFT': new_head = (head_y, head_x - 1)
        elif self.direction == 'RIGHT': new_head = (head_y, head_x + 1)
        
        self.body.insert(0, new_head)
        self.body.pop()

    def grow(self):
        """Makes the snake grow by one segment."""
        self.body.append(self.body[-1])
        self.score += 1

    def set_direction(self, new_direction):
        """Sets a new direction, preventing 180-degree turns."""
        opposites = {'UP': 'DOWN', 'DOWN': 'UP', 'LEFT': 'RIGHT', 'RIGHT': 'LEFT'}
        if len(self.body) > 1 and new_direction == opposites.get(self.direction):
            return
        self.direction = new_direction

    def check_collision(self, other_snakes):
        """Checks for collisions with walls, self, or other snakes."""
        head = self.body[0]

        if not (0 <= head[0] < HEIGHT and 0 <= head[1] < WIDTH):
            self.is_alive = False
            return

        if head in self.body[1:]:
            self.is_alive = False
            return

        for other in other_snakes:
            if head in other.body:
                self.is_alive = False
                return

    def respawn(self, x, y):
        """Resets the snake to its initial state at a new position."""
        self.body = [(y, x - i) for i in range(INITIAL_SNAKE_LENGTH)]
        self.direction = random.choice(['UP', 'DOWN', 'LEFT', 'RIGHT'])
        self.is_alive = True
        self.score = 0