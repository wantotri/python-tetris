# Python Tetris

![](./assets/python-tetris.gif)

Created using Python 3.10.4

## How to Run the Game
In this project root directory:
1. [optional] Install and create virtual environment (venv)
2. Install dependencies `pip install -r requirements.txt`
3. Run the script `py tetris.py`

## In-game Keyboard Shortcut
* Create New Game: key `n` or `N`
* Pause/Resume the game: key `p` or `P`
* Move block left: left arrow key `(⬅)`
* Move block right: right arrow key `(➡)`
* Move block bottom: down arrow key `(⬇)`
* Rotate block: key `r` or `R`

## Create Stand Alone Executable
* Install dev dependencies `pip install -r requirements_dev.txt`
* Run `pyinstaller --onefile tetris.py`
* Copy `assets` dir to `dist` dir