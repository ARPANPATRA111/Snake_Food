# Terminal Snake 🐍: A Multiplayer ASCII Showdown

This project is a real-time, terminal-based multiplayer Snake game built entirely in Python. It uses a client-server architecture to allow multiple players to compete simultaneously in the same game world, rendered with classic ASCII graphics.


https://github.com/user-attachments/assets/7eb8a51d-1c32-4413-a128-3efe895b87d2


## Why This Project❓

After organizing an 8-hour hackathon for our Development Club (DC), I was incredibly inspired by the energy and the problem statements presented. I didn't get to build a project during the event itself, so I decided to tackle one of the challenges afterward. This project is my way of diving back into development, sharpening my logic skills, and bringing an exciting hackathon idea to life!

## 🎯 Problem Statement

The goal was to build a real-time multiplayer game that runs entirely in the terminal, using a client-server architecture to connect players and manage the game state.

### Deliverables
* Source code.
* A live demo of a working game with at least 2 players connected over a network.
* Brief documentation explaining the game rules and network architecture.

### Constraints
* All graphics must be rendered using standard terminal ASCII characters.
* Must support at least 2 simultaneous players.
* Must be implemented using a client-server model (e.g., using sockets with TCP for reliability).

## 💡 Key Learnings
This project was a fantastic exercise in networking, concurrency, and terminal UI design. I've documented the core concepts I learned and the technical challenges I solved in a separate file.

➡️ **[Read about my Learning Journey here](./learning.md)**

## 🚀 Getting Started

Follow these steps to get the game running on your local machine.

### ✅ Prerequisites

* **Python 3.x**

* **Standard Libraries:** This project uses several built-in Python libraries, so no installation is needed for them:
    * `socket`
    * `threading`
    * `json`
    * `time`
    * `random`
    * `signal`
    * `sys`
    * `logging`

* **Curses Library:** This library is used for the terminal graphics.
    * **Linux & macOS:** The `curses` library comes pre-installed.
    * **Windows:** You need to install the `windows-curses` library. You can do this using pip:
      
        ```bash
        pip install windows-curses
        ```

### ⚙️ Installation & Setup

1.  **Clone the Repository**
    ```bash
    git clone <your-repository-url>
    cd <repository-folder>
    ```

2.  **Start the Server**
    Open a terminal and run the server script. It will begin listening for connections.
    ```bash
    python server.py
    ```

3.  **Start the Clients**
    Open a **new terminal** for each player and run the client script.
    ```bash
    python client.py
    ```
    Repeat this step in another new terminal for a second player to join the game.

**Note:** The server is currently configured for local play (`127.0.0.1`). To play over a network, you would need to change the `SERVER_HOST` in `client.py` to the server's local IP address and ensure your network settings (like firewalls) allow the connection.

## 🎮 Controls

* **Arrow Keys:** Change the direction of your snake.
* **'q' Key:** Quit the game.
* **'r' Key:** Respawn after your snake has been eliminated.
