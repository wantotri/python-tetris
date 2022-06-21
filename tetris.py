import PySimpleGUI as sg
from pydantic import BaseModel
from types import SimpleNamespace
from time import time
from random import choice
from math import cos, sin, radians
from collections import defaultdict

UNIT_SIZE = 20
BORDER_SIZE = 4
BOARD_WIDTH = 10
BOARD_HEIGHT = 24
ENTRY_POS = (int((BOARD_WIDTH-1)/2), BOARD_HEIGHT+2)
INITIAL_GAME_SPEED = 0.4  # smaller = faster
ACCELERATION_FACTOR = 0.1
ACCELERATION_SCORE = 100
ROTATION_ADJUSTMENT = 2

cell = SimpleNamespace(size=UNIT_SIZE, color='lightgray')
border = SimpleNamespace(size=BORDER_SIZE, color='gray')
board = SimpleNamespace(width=UNIT_SIZE*BOARD_WIDTH, height=UNIT_SIZE*BOARD_HEIGHT, color='black')

class Tetromino(BaseModel):
    name: str
    anchor: tuple[int, int]
    shape: list[tuple[int, int]]
    color: str

    def get_pos(self):
        return [(self.anchor[0]+unit[0], self.anchor[1]+unit[1]) for unit in self.shape]

# Initialize all the block types
tetro_T = Tetromino(name='T', anchor=ENTRY_POS, shape=[(0, 0), (0, -1), (0, -2), (1, -1)], color='red')
tetro_L = Tetromino(name='L', anchor=ENTRY_POS, shape=[(0, 0), (0, -1), (0, -2), (1, -2)], color='orange')
tetro_J = Tetromino(name='J', anchor=ENTRY_POS, shape=[(0, 0), (0, -1), (0, -2), (-1, -2)], color='brown')
tetro_O = Tetromino(name='O', anchor=ENTRY_POS, shape=[(0, 0), (0, -1), (1, 0), (1, -1)], color='green')
tetro_I = Tetromino(name='I', anchor=ENTRY_POS, shape=[(0, 0), (0, -1), (0, -2), (0, -3)], color='blue')
tetro_S = Tetromino(name='S', anchor=ENTRY_POS, shape=[(0, 0), (0, -1), (1, -1), (1, -2)], color='darkcyan')
tetro_Z = Tetromino(name='Z', anchor=ENTRY_POS, shape=[(0, 0), (0, -1), (-1, -1), (-1, -2)], color='purple')

tetrominoes = [tetro_T, tetro_L, tetro_J, tetro_O, tetro_I, tetro_S, tetro_Z]

def pos_to_pixel(x: int, y: int):
    width = UNIT_SIZE
    height = UNIT_SIZE
    border = BORDER_SIZE
    tl = ((x*width)+border, ((y+1)*height)-border)
    br = (((x+1)*width)-border, (y*height)+border)
    return tl, br

def draw_rectangle(graph: sg.Graph, x: int, y: int, color=None):
    tl, br = pos_to_pixel(x, y)
    return graph.draw_rectangle(
        top_left=tl,
        bottom_right=br,
        fill_color=cell.color,
        line_color=border.color if color is None else color,
        line_width=border.size)

def draw_block(graph: sg.Graph, pos_list, color=None):
    return [draw_rectangle(graph, pos[0], pos[1], color) for pos in pos_list]

def get_block_bounding_box(graph: sg.Graph, block_id_list):
    l, t, r, b = board.width, 0, 0, board.height
    for block_id in block_id_list:
        (l0, t0), (r0, b0) = graph.get_bounding_box(block_id)
        l = min(l, l0)
        t = max(t, t0)
        r = max(r, r0)
        b = min(b, b0)
    return (l, t), (r, b)

def can_move_left(graph: sg.Graph, blocks: list[int]) -> bool:
    for block_id in blocks:
        (l, _), (_, b) = graph.get_bounding_box(block_id)
        if l < 10: return False
        figures = graph.get_figures_at_location((l-UNIT_SIZE+1, b+1))
        if figures and figures[0] not in blocks: return False
    return True

def can_move_right(graph: sg.Graph, blocks: list[int]) -> bool:
    for block_id in blocks:
        (l, _), (r, b) = graph.get_bounding_box(block_id)
        if r > board.width-10: return False
        figures = graph.get_figures_at_location((l+UNIT_SIZE+1, b+1))
        if figures and figures[0] not in blocks: return False
    return True

def can_move_down(graph: sg.Graph, blocks: list[int]) -> bool:
    for block_id in blocks:
        (l, _), (_, b) = graph.get_bounding_box(block_id)
        if b < 10: return False
        figures = graph.get_figures_at_location((l+1, b-UNIT_SIZE+1))
        if figures and figures[0] not in blocks: return False
    return True

def rotate_point(origin, point, angle=-90):
    """Rotate a point counterclockwise by a given angle around a given origin.
    The angle should be given in radians."""
    ox, oy = origin
    px, py = point
    angle = radians(angle)
    qx = int(ox + cos(angle) * (px - ox) - sin(angle) * (py - oy))
    qy = int(oy + sin(angle) * (px - ox) + cos(angle) * (py - oy))
    # this '3' is adjustment to the pySimpleGUI grid system
    return qx+ROTATION_ADJUSTMENT, qy-ROTATION_ADJUSTMENT

def can_rotate(graph: sg.Graph, blocks: list[int]) -> bool:
    # Check the origin againts the board boundaries
    origin, (r, b) = graph.get_bounding_box(blocks[1])
    if origin[0] < 10 or b <10 or r > board.width-10: return False

    for block_id in blocks:
        tl, _ = graph.get_bounding_box(block_id)
        x, y = rotate_point(origin, tl)
        if x < 0: return False
        figures = graph.get_figures_at_location((x+1, y+1))
        if figures and figures[0] not in blocks: return False
    return True

def move_blocks(graph: sg.Graph, blocks: list[int], x: int, y: int):
    for bid in blocks: graph.move_figure(bid, x, y)

def main():
    ### GAME SETUP
    filled = defaultdict(list)
    lose = False
    score = 0
    game_speed = INITIAL_GAME_SPEED
    speed_counter = 1

    ### GAME GUI
    sg.theme('DarkAmber')

    main_board = sg.Graph(
        canvas_size=(board.width, board.height),
        graph_bottom_left=(0, 0),
        graph_top_right=(board.width, board.height),
        background_color=board.color,
        key='-MAIN_BOARD-')

    next_board = sg.Graph(
        canvas_size=(UNIT_SIZE*3, UNIT_SIZE*4),
        graph_bottom_left=((BOARD_WIDTH-7)*UNIT_SIZE, (BOARD_HEIGHT-1)*UNIT_SIZE),
        graph_top_right=((BOARD_WIDTH-4)*UNIT_SIZE, (BOARD_HEIGHT+3)*UNIT_SIZE),
        background_color=board.color,
        key='-NEXT_BOARD-')

    newgame_btn = sg.Button('⚡ Start', size=(11,1), key='-NEWGAME-')
    pause_btn = sg.Button('⏸ Pause', size=(11,1), key='-PAUSE-', visible=False)
    prompt_text = sg.Text('Click "Start" to play\n', key='-TEXT1-')

    layout = [
        [newgame_btn, pause_btn],
        [prompt_text],
        [main_board, next_board]
    ]

    window = sg.Window(
        title='Python Tetris',
        layout=layout,
        font=('Helvetica', 10),
        return_keyboard_events=True,
        finalize=True)

    window.bind("<KeyPress-Down>", "LongDown")
    window.bind("<KeyPress-Left>", "LongLeft")
    window.bind("<KeyPress-Right>", "LongRight")

    # Initial Screen Banner
    info_text = '🚀 github: wantotri\n' \
                '📷 ig: @wantotrees'
    main_board.draw_image('assets/logo-small.png', location=(board.width/4, board.height/2+60))
    main_board.draw_text(info_text, (board.width/2, board.height/2), color='lightgrey',
                         font=('Consolas', 10))

    ### GAME LOOP
    start_time = time()
    timeout = None

    # Event Loop to process "events" and get the "values" of the inputs
    while True:
        event, values = window.read(timeout=timeout)

        if event == sg.WIN_CLOSED: break

        if event == '-NEWGAME-' or event in 'nN':
            filled = defaultdict(list)
            lose = False
            score = 0
            game_speed = INITIAL_GAME_SPEED
            speed_counter = 1

            window['-PAUSE-'].update(visible=True)
            window['-TEXT1-'].update('Score: 0\nSpeed: 1')

            main_board.erase()
            next_board.erase()
            tetro = choice(tetrominoes)
            blocks = draw_block(main_board, tetro.get_pos(), tetro.color)
            next_tetro = choice(tetrominoes)
            draw_block(next_board, next_tetro.get_pos(), next_tetro.color)

            timeout = 10
            start_time = time()

        if event == '-PAUSE-' or event in 'pP':
            if timeout is None:
                window['-PAUSE-'].update('⏸ Pause')
                timeout = 10
            else:
                window['-PAUSE-'].update('▶ Resume')
                timeout = None

        if timeout is None: continue

        if event in 'rR':
            if can_rotate(main_board, blocks):
                origin, _ = main_board.get_bounding_box(blocks[1])
                for bid in blocks:
                    tl, _ = main_board.get_bounding_box(bid)
                    x, y = rotate_point(origin, tl)
                    main_board.relocate_figure(bid, x, y)

        if event == 'LongLeft':
            if can_move_left(main_board, blocks):
                move_blocks(main_board, blocks, -UNIT_SIZE, 0)

        if event == 'LongRight':
            if can_move_right(main_board, blocks):
                move_blocks(main_board, blocks, UNIT_SIZE, 0)

        if event == 'LongDown':
            if can_move_down(main_board, blocks):
                move_blocks(main_board, blocks, 0, -UNIT_SIZE)

        # GAME TICKS
        if not lose and time() - start_time >= game_speed:
            (_, t), _ = get_block_bounding_box(main_board, blocks)

            if can_move_down(main_board, blocks):
                move_blocks(main_board, blocks, 0, -UNIT_SIZE)

            elif t >= board.height-10:
                main_board.erase()
                next_board.erase()
                main_board.draw_text('GAME\nOVER', location=(board.width/2, board.height/2+30),
                                     font=('Consolas', 24), color='lightgrey')
                main_board.draw_text(f'Your Score: {score}', location=(board.width/2, board.height/2-30),
                                     font=('Consolas', 12), color='lightgrey')

                window['-PAUSE-'].update(visible=False)
                lose = True
                timeout = None

            else:
                for bid in blocks:
                    _, (_, b) = main_board.get_bounding_box(bid)
                    filled[int(b/UNIT_SIZE)].append(bid)

                print('-'*20)
                for row, block_ids in sorted(filled.items()):
                    print(f'row: {row} -> len: {len(filled[row])} -> {filled[row]}')
                    if len(block_ids) == BOARD_WIDTH:
                        for idx in block_ids:
                            main_board.delete_figure(idx)
                        filled[row] = []
                        score += 10
                        if score and score%ACCELERATION_SCORE == 0:
                            game_speed = game_speed - (game_speed*ACCELERATION_FACTOR)
                            speed_counter += 1
                        window['-TEXT1-'].update(f'Score: {score}\nSpeed: {speed_counter}')

                    elif row-4 >= 0 and not filled[row-4]:
                        move_blocks(main_board, block_ids, 0, -UNIT_SIZE*4)
                        filled[row-4] = filled[row]
                        filled[row] = []

                    elif row-3 >= 0 and not filled[row-3]:
                        move_blocks(main_board, block_ids, 0, -UNIT_SIZE*3)
                        filled[row-3] = filled[row]
                        filled[row] = []

                    elif row-2 >= 0 and not filled[row-2]:
                        move_blocks(main_board, block_ids, 0, -UNIT_SIZE*2)
                        filled[row-2] = filled[row]
                        filled[row] = []

                    elif row-1 >= 0 and not filled[row-1]:
                        move_blocks(main_board, block_ids, 0, -UNIT_SIZE*1)
                        filled[row-1] = filled[row]
                        filled[row] = []

                blocks = draw_block(main_board, next_tetro.get_pos(), next_tetro.color)
                next_board.erase()
                next_tetro = choice(tetrominoes)
                draw_block(next_board, next_tetro.get_pos(), next_tetro.color)

            start_time = time()

    window.close()


if __name__ == '__main__':
    main()