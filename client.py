import socket
import json
from typing import ClassVar

from rich.text import Text
from textual.app import App, ComposeResult
from textual.containers import Container, Vertical
from textual.widget import Widget
from textual.widgets import Header, Footer, Static, Label, Button
from textual.screen import ModalScreen
from textual.message import Message
from game_logic import WIDTH, HEIGHT, SNAKE_BODY_SYMBOL, SNAKE_HEAD_SYMBOL, FOOD_SYMBOL


SERVER_HOST = '127.0.0.1' 
SERVER_PORT = 12345
MESSAGE_DELIM_BYTES = b'\n'

SNAKE_COLORS = [
    "bright_red", "bright_green", "bright_yellow", "bright_blue",
    "bright_magenta", "bright_cyan"
]

class GameStateUpdate(Message):
    def __init__(self, state: dict) -> None:
        self.state = state
        super().__init__()

class WelcomeInfo(Message):
    def __init__(self, player_id: int) -> None:
        self.player_id = player_id
        super().__init__()

class ConnectionError(Message):
    pass

class GameBoard(Widget):
    game_state = None
    
    def render(self) -> Text:
        if not self.game_state:
            top_border = "┌" + "─" * WIDTH + "┐"
            middle = "│" + "Connecting...".center(WIDTH) + "│"
            bottom_border = "└" + "─" * WIDTH + "┘"
            blank_lines = ["│" + " " * WIDTH + "│" for _ in range(HEIGHT - 1)]
            return Text("\n".join([top_border, middle] + blank_lines + [bottom_border]))

        canvas = [list(" " * WIDTH) for _ in range(HEIGHT)]
        
        food_y, food_x = self.game_state['food']
        if 0 <= food_y < HEIGHT and 0 <= food_x < WIDTH:
            canvas[food_y][food_x] = FOOD_SYMBOL
        
        for pid_str, snake_data in self.game_state['snakes'].items():
            if snake_data['is_alive']:
                for i, (y, x) in enumerate(snake_data['body']):
                    if 0 <= y < HEIGHT and 0 <= x < WIDTH:
                        symbol = SNAKE_HEAD_SYMBOL if i == 0 else SNAKE_BODY_SYMBOL
                        canvas[y][x] = symbol

        top_border = Text("┌" + "─" * WIDTH + "┐\n", style="blue")
        bottom_border = Text("└" + "─" * WIDTH + "┘", style="blue")
        
        final_text = Text()
        final_text.append(top_border)

        for i, row in enumerate(canvas):
            final_text.append("│", style="blue")
            row_text = Text("".join(row))
            for pid_str, snake_data in self.game_state['snakes'].items():
                if snake_data['is_alive']:
                    pid = int(pid_str)
                    color = SNAKE_COLORS[pid % len(SNAKE_COLORS)]
                    for y, x in snake_data['body']:
                        if y == i:
                            row_text.stylize(color, x, x + 1)
            if food_y == i:
                row_text.stylize("green", food_x, food_x + 1)

            final_text.append(row_text)
            final_text.append("│\n", style="blue")

        final_text.append(bottom_border)
        return final_text

class Scoreboard(Static):
    def update_scores(self, game_state: dict, my_player_id: int):
        lines = []
        if not game_state or my_player_id is None:
            self.update("Loading scores...")
            return
        sorted_pids = sorted(game_state['snakes'].keys(), key=int)
        for pid_str in sorted_pids:
            pid = int(pid_str)
            snake = game_state['snakes'][pid_str]
            is_me = (pid == my_player_id)
            status = "✅" if snake['is_alive'] else "💀"
            score_text = f"Player {pid}{' (You)' if is_me else ''} {status}: {snake['score']}"
            style = "bold yellow" if is_me else "white"
            lines.append(Text(score_text, style=style))
        self.update("\n".join(line.plain for line in lines))

class GameOverScreen(ModalScreen):
    def __init__(self, final_score: int) -> None:
        self.final_score = final_score
        super().__init__()
    def compose(self) -> ComposeResult:
        yield Vertical(
            Label("GAME OVER", id="game_over_label"),
            Label(f"Final Score: {self.final_score}", id="final_score_label"),
            Button("Replay", variant="success", id="replay"),
            Button("Quit", variant="error", id="quit"),
            id="game_over_dialog",
        )
    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "replay")

class SnakeApp(App):
    CSS_PATH = "snake.tcss"
    BINDINGS: ClassVar = [
        ("up", "direction('UP')", "Move Up"),
        ("down", "direction('DOWN')", "Move Down"),
        ("left", "direction('LEFT')", "Move Left"),
        ("right", "direction('RIGHT')", "Move Right"),
    ]

    def __init__(self):
        super().__init__()
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.game_state = None
        self.my_player_id = None
        self.is_game_over = False

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Container(
            GameBoard(id="game_board"),
            Scoreboard(id="scoreboard"),
            id="app-container"
        )
        yield Footer()
        
    def action_quit(self) -> None:
        try:
            self.client_socket.shutdown(socket.SHUT_RDWR)
            self.client_socket.close()
        except OSError:
            pass
        self.exit()

    def on_mount(self) -> None:
        try:
            self.client_socket.connect((SERVER_HOST, SERVER_PORT)) # connecting to the servers socket
            self.run_worker(self.receive_updates, thread=True)
        except ConnectionRefusedError:
            self.exit("Connection refused. Is the server running?") # when u run the Client but server is off

    def action_direction(self, direction: str) -> None:
        if not self.is_game_over:
            self.send_command(direction)

    def send_command(self, command: str):
        try:
            self.client_socket.sendall(command.encode('utf-8') + MESSAGE_DELIM_BYTES) # sending the command to the server
        except OSError:
            self.exit("Connection lost.")

    def on_game_state_update(self, message: GameStateUpdate) -> None:
        self.game_state = message.state
        self.query_one(GameBoard).game_state = self.game_state
        self.query_one(GameBoard).refresh()
        self.query_one(Scoreboard).update_scores(self.game_state, self.my_player_id)
        
        if self.my_player_id is not None:
            my_snake = self.game_state['snakes'].get(str(self.my_player_id))
            if my_snake and not my_snake['is_alive'] and not self.is_game_over:
                self.is_game_over = True
                final_score = my_snake.get('score', 0)
                self.push_screen(GameOverScreen(final_score), self.handle_game_over_result)

    def on_welcome_info(self, message: WelcomeInfo) -> None:
        self.my_player_id = message.player_id
        self.query_one(Footer).key_text = f"Connected as Player {self.my_player_id} | Press CTRL+C to Quit"

    def on_connection_error(self, message: ConnectionError) -> None:
        self.exit("Connection to server lost.")

    def handle_game_over_result(self, should_replay: bool) -> None:
        if should_replay:
            self.send_command("RESPAWN")
            self.is_game_over = False
        else:
            self.action_quit()

    def receive_updates(self) -> None:
        buffer = b''
        while True:
            try:
                data = self.client_socket.recv(4096)
                if not data: break
                buffer += data
                while MESSAGE_DELIM_BYTES in buffer:
                    line_bytes, buffer = buffer.split(MESSAGE_DELIM_BYTES, 1)
                    line = line_bytes.decode('utf-8')
                    if not line: continue
                    state = json.loads(line)
                    if state.get('type') == 'welcome':
                        self.post_message(WelcomeInfo(state['player_id']))
                    elif state.get('type') == 'game_state':
                        self.post_message(GameStateUpdate(state))
            except (OSError, json.JSONDecodeError):
                break
        self.post_message(ConnectionError())

if __name__ == "__main__":
    app = SnakeApp()
    app.run()