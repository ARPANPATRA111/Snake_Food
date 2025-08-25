import socket
import curses
import json
import threading
import time
import logging
from game_logic import WIDTH, HEIGHT, SNAKE_SYMBOL, FOOD_SYMBOL

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='client_debug.log',
    filemode='w' 
)

SERVER_HOST = '127.0.0.1' 
SERVER_PORT = 12345
MESSAGE_DELIM = '\n'

latest_game_state = None
my_player_id = None
state_lock = threading.Lock()
client_running = True

def receive_updates(client_socket):
    """Receives and processes game state updates from the server."""
    global latest_game_state, my_player_id, client_running
    buffer = ""
    logging.info("Receiver thread started.")
    while client_running:
        try:
            data = client_socket.recv(4096).decode('utf-8', errors='ignore')
            if not data:
                logging.warning("Received no data. Server likely closed connection.")
                break
            buffer += data
            while MESSAGE_DELIM in buffer:
                line, buffer = buffer.split(MESSAGE_DELIM, 1)
                if not line: continue
                try:
                    state = json.loads(line)
                    logging.info(f"Successfully decoded JSON: {line}")
                    with state_lock:
                        if state.get('type') == 'welcome':
                            my_player_id = state.get('player_id')
                            logging.info(f"Received welcome message. My Player ID is {my_player_id}")
                        elif state.get('type') == 'game_state':
                            latest_game_state = state
                except json.JSONDecodeError:
                    logging.error(f"JSON DECODE ERROR on data: {line}")
                    pass
        except (socket.timeout, ConnectionResetError, OSError) as e:
            logging.error(f"Socket error in receiver thread: {e}", exc_info=True)
            break
    client_running = False
    logging.info("Receiver thread stopped.")


def draw_text(stdscr, y, x, text, color_pair=0):
    """Safely draws text on the curses screen."""
    try:
        stdscr.addstr(y, x, text, color_pair)
    except curses.error: pass

def draw_game(stdscr, game_state_enum):
    """Draws the entire game screen, including borders, food, snakes, and scores."""
    stdscr.clear()
    if curses.has_colors():
        curses.start_color()
        curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK) # Food
        curses.init_pair(2, curses.COLOR_RED, curses.COLOR_BLACK)   # Game Over Text
        curses.init_pair(3, curses.COLOR_YELLOW, curses.COLOR_BLACK)# Your Score

    for y in range(HEIGHT + 2):
        draw_text(stdscr, y, 0, '#')
        draw_text(stdscr, y, WIDTH + 1, '#')
    for x in range(WIDTH + 2):
        draw_text(stdscr, 0, x, '#')
        draw_text(stdscr, HEIGHT + 1, x, '#')

    with state_lock:
        state = latest_game_state

    if not state:
        draw_text(stdscr, 1, 2, "Connecting to server...")
        stdscr.refresh()
        return

    food_y, food_x = state['food']
    draw_text(stdscr, food_y + 1, food_x + 1, FOOD_SYMBOL, curses.color_pair(1))

    score_line = 1
    sorted_pids = sorted(state['snakes'].keys(), key=int)
    for pid_str in sorted_pids:
        pid = int(pid_str)
        snake = state['snakes'][pid_str]
        is_me = (pid == my_player_id)
        
        status = "ALIVE" if snake.get('is_alive') else "DEAD"
        score_text = f"Player {pid}{' (You)' if is_me else ''} [{status}]: {snake.get('score', 0)}"
        color = curses.color_pair(3) if is_me else 0
        draw_text(stdscr, score_line, WIDTH + 4, score_text, color)
        score_line += 1

        if snake.get('is_alive'):
            for y, x in snake.get('body', []):
                draw_text(stdscr, y + 1, x + 1, SNAKE_SYMBOL)
    
    if game_state_enum == 'GAME_OVER':
        msg1 = "GAME OVER"
        msg2 = "Press 'R' to Replay or 'Q' to Quit"
        draw_text(stdscr, HEIGHT // 2, (WIDTH + 2 - len(msg1)) // 2, msg1, curses.color_pair(2))
        draw_text(stdscr, HEIGHT // 2 + 1, (WIDTH + 2 - len(msg2)) // 2, msg2)

    stdscr.refresh()

def main(stdscr):
    """Main function to run the client application."""
    global client_running
    logging.info("Client main function started.")
    curses.curs_set(0)
    stdscr.nodelay(True)

    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        client_socket.connect((SERVER_HOST, SERVER_PORT))
        logging.info(f"Successfully connected to server at {SERVER_HOST}:{SERVER_PORT}")
    except ConnectionRefusedError as e:
        logging.error(f"Connection refused: {e}")
        print("Connection refused. Is the server running at that address?")
        time.sleep(3)
        return

    threading.Thread(target=receive_updates, args=(client_socket,), daemon=True).start()
    game_state_enum = 'PLAYING'

    while client_running:
        is_player_alive = True
        with state_lock:
            if latest_game_state and my_player_id is not None:
                my_snake = latest_game_state['snakes'].get(str(my_player_id))
                if my_snake and not my_snake['is_alive']:
                    is_player_alive = False

        if not is_player_alive and game_state_enum == 'PLAYING':
            game_state_enum = 'GAME_OVER'

        key = stdscr.getch()
        command = None
        
        if game_state_enum == 'PLAYING':
            if key == curses.KEY_UP: command = 'UP'
            elif key == curses.KEY_DOWN: command = 'DOWN'
            elif key == curses.KEY_LEFT: command = 'LEFT'
            elif key == curses.KEY_RIGHT: command = 'RIGHT'
            elif key == ord('q'): client_running = False
        
        elif game_state_enum == 'GAME_OVER':
            if key == ord('q'): client_running = False
            elif key == ord('r'):
                command = 'RESPAWN'
                game_state_enum = 'PLAYING'

        if command:
            try:
                client_socket.sendall((command + MESSAGE_DELIM).encode('utf-8'))
            except OSError:
                client_running = False

        draw_game(stdscr, game_state_enum)
        time.sleep(1 / 60)

    client_socket.close()
    logging.info("Client main function finished.")

if __name__ == '__main__':
    try:
        curses.wrapper(main)
    except curses.error:
        print("Error: Your terminal window is too small.")
    finally:
        print("Game exited. Check client_debug.log for details.")