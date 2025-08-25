import socket
import threading
import time
import json
import random
import signal
import sys
from game_logic import Snake, WIDTH, HEIGHT

HOST = '0.0.0.0'
PORT = 12345
TICK_RATE = 10
MESSAGE_DELIM = b'\n'

# --- Global State Variables ---
clients = {}
snakes = {}
food_pos = (0, 0)
game_state_lock = threading.Lock()
next_player_id = 0
server_running = True
server_socket = None

def spawn_food():
    """
    Spawns food in a random, unoccupied location. This version is safe
    and does NOT cause a deadlock, as it assumes the lock is already held.
    """
    global food_pos
    occupied_coords = set()
    for snake in snakes.values():
        if snake.is_alive:
            occupied_coords.update(snake.body)

    all_coords = [(y, x) for y in range(HEIGHT) for x in range(WIDTH)]
    available_coords = [pos for pos in all_coords if pos not in occupied_coords]

    if available_coords:
        food_pos = random.choice(available_coords)
    else:
        print("[GAME INFO] No space left to spawn food!")
        food_pos = (-1, -1)

def handle_client(conn, player_id):
    """Handles all communication for a single connected client."""
    print(f"[NEW CONNECTION] Player {player_id} connected from {conn.getpeername()}.")
    try:
        welcome_msg = json.dumps({'type': 'welcome', 'player_id': player_id}).encode('utf-8') + MESSAGE_DELIM
        conn.sendall(welcome_msg)
    except OSError:
        pass

    buffer = b''
    conn.settimeout(1.0)
    try:
        while server_running:
            try:
                data = conn.recv(1024)
                if not data: break
                buffer += data
            except socket.timeout: continue

            while MESSAGE_DELIM in buffer:
                cmd_bytes, buffer = buffer.split(MESSAGE_DELIM, 1)
                cmd = cmd_bytes.decode('utf-8', errors='ignore').strip().upper()

                with game_state_lock:
                    if player_id not in snakes: continue
                    if cmd in ('UP', 'DOWN', 'LEFT', 'RIGHT'):
                        if snakes[player_id].is_alive:
                            snakes[player_id].set_direction(cmd)
                    elif cmd == 'RESPAWN' and not snakes[player_id].is_alive:
                        start_y = random.randint(5, HEIGHT - 6)
                        start_x = random.randint(5, WIDTH - 6)
                        snakes[player_id].respawn(start_x, start_y)
    finally:
        print(f"[CONNECTION CLOSED] Player {player_id} has left.")
        with game_state_lock:
            if player_id in snakes: snakes[player_id].is_alive = False
            clients.pop(conn, None)
        try:
            conn.close()
        except OSError: pass

def game_loop():
    """The main server loop that updates and broadcasts the game state."""
    with game_state_lock:
        spawn_food()

    while server_running:
        start_time = time.time()
        msg_data = None
        current_clients = []

        with game_state_lock:
            active_snakes = {pid: s for pid, s in snakes.items() if s.is_alive}
            for pid, snake in active_snakes.items():
                snake.move()
                if snake.body[0] == food_pos:
                    snake.grow()
                    spawn_food()
                others = [s for p2, s in active_snakes.items() if p2 != pid]
                snake.check_collision(others)

            broadcast_state = {
                'type': 'game_state',
                'snakes': {pid: s.to_dict() for pid, s in snakes.items()},
                'food': food_pos
            }
            msg_data = json.dumps(broadcast_state).encode('utf-8') + MESSAGE_DELIM
            current_clients = list(clients.keys())

        for conn in current_clients:
            try:
                conn.sendall(msg_data)
            except (ConnectionResetError, BrokenPipeError, OSError):
                with game_state_lock:
                    pid = clients.pop(conn, None)
                    if pid and pid in snakes:
                        snakes[pid].is_alive = False
                    print(f"[PRUNING] Removing dead connection for Player {pid}.")
                    try:
                        conn.close()
                    except OSError:
                        pass
        
        elapsed = time.time() - start_time
        delay = (1.0 / TICK_RATE) - elapsed
        if delay > 0: time.sleep(delay)

def shutdown_server(sig=None, frame=None):
    """Gracefully shuts down the server on Ctrl+C."""
    global server_running
    print("\n[SHUTDOWN] Interrupt received, shutting down...")
    server_running = False
    if server_socket:
        try: server_socket.close()
        except OSError: pass
    print("[SHUTDOWN] Server has been closed.")

def main():
    """Initializes and starts the server."""
    global next_player_id, server_socket
    signal.signal(signal.SIGINT, shutdown_server)
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((HOST, PORT))
    server_socket.settimeout(1.0)
    server_socket.listen()
    print(f"[*] Server listening on {HOST}:{PORT}")

    threading.Thread(target=game_loop, daemon=True).start()

    while server_running:
        try:
            conn, addr = server_socket.accept()
            with game_state_lock:
                pid = next_player_id
                clients[conn] = pid
                start_y = random.randint(5, HEIGHT - 6)
                start_x = random.randint(5, WIDTH - 6)
                snakes[pid] = Snake(pid, start_x, start_y)
                next_player_id += 1
            threading.Thread(target=handle_client, args=(conn, pid), daemon=True).start()
        except socket.timeout: continue
        except OSError: break

    print("[MAIN THREAD] Exiting.")

if __name__ == '__main__':
    main()