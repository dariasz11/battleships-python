"""Battleships desktop game implemented with the Python standard library."""

from __future__ import annotations

import random
import tkinter as tk
from dataclasses import dataclass
from tkinter import messagebox, ttk


GRID_SIZE = 10
SHIPS = {
    "Carrier": 5,
    "Battleship": 4,
    "Cruiser": 3,
    "Submarine": 3,
    "Destroyer": 2,
}

WATER = "#0b4f71"
WATER_HOVER = "#167ca5"
SHIP = "#7d8b99"
HIT = "#d64545"
MISS = "#d9edf7"
SUNK = "#7f1d1d"
PANEL = "#102a43"
ACCENT = "#f0b429"


Cell = tuple[int, int]


@dataclass
class Vessel:
    name: str
    cells: set[Cell]

    def is_sunk(self, shots: set[Cell]) -> bool:
        return self.cells <= shots


def cells_for(row: int, col: int, size: int, orientation: str) -> set[Cell]:
    if orientation == "H":
        return {(row, col + offset) for offset in range(size)}
    return {(row + offset, col) for offset in range(size)}


def valid_cells(cells: set[Cell], occupied: set[Cell]) -> bool:
    return (
        len(cells) > 0
        and all(0 <= row < GRID_SIZE and 0 <= col < GRID_SIZE for row, col in cells)
        and cells.isdisjoint(occupied)
    )


def random_fleet(rng: random.Random | None = None) -> list[Vessel]:
    rng = rng or random.Random()
    fleet: list[Vessel] = []
    occupied: set[Cell] = set()
    for name, size in SHIPS.items():
        while True:
            orientation = rng.choice(("H", "V"))
            row = rng.randrange(GRID_SIZE)
            col = rng.randrange(GRID_SIZE)
            cells = cells_for(row, col, size, orientation)
            if valid_cells(cells, occupied):
                fleet.append(Vessel(name, cells))
                occupied.update(cells)
                break
    return fleet


class BattleshipsApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Battleships")
        self.geometry("1180x760")
        self.minsize(1050, 700)
        self.configure(bg="#071a2b")
        self.current_frame: tk.Frame | None = None
        self.protocol("WM_DELETE_WINDOW", self.confirm_exit)
        self.show_start()
        self.after_idle(self.maximize_window)

    def maximize_window(self) -> None:
        """Open maximized on Windows while retaining a portable fallback."""
        try:
            self.state("zoomed")
        except tk.TclError:
            self.geometry(
                f"{self.winfo_screenwidth()}x{self.winfo_screenheight()}+0+0"
            )

    def show(self, frame_type: type[tk.Frame], *args: object) -> None:
        if self.current_frame is not None:
            self.current_frame.destroy()
        self.current_frame = frame_type(self, *args)
        self.current_frame.pack(fill="both", expand=True)

    def show_start(self) -> None:
        self.show(StartScreen)

    def show_rules(self) -> None:
        self.show(RulesScreen)

    def show_placement(self) -> None:
        self.show(PlacementScreen)

    def show_game(self, fleet: list[Vessel]) -> None:
        self.show(GameScreen, fleet)

    def confirm_exit(self) -> None:
        if messagebox.askyesno("Exit", "Do you want to close the game?"):
            self.destroy()


class BaseScreen(tk.Frame):
    def __init__(self, app: BattleshipsApp) -> None:
        super().__init__(app, bg="#071a2b")
        self.app = app

    def title_label(self, text: str, subtitle: str = "") -> None:
        tk.Label(
            self,
            text=text,
            bg="#071a2b",
            fg="white",
            font=("Segoe UI", 34, "bold"),
        ).pack(pady=(42, 6))
        if subtitle:
            tk.Label(
                self,
                text=subtitle,
                bg="#071a2b",
                fg="#b8d8e8",
                font=("Segoe UI", 13),
            ).pack(pady=(0, 24))

    @staticmethod
    def action(parent: tk.Misc, text: str, command: object, width: int = 22) -> tk.Button:
        return tk.Button(
            parent,
            text=text,
            command=command,
            width=width,
            bg=ACCENT,
            fg="#102a43",
            activebackground="#ffd166",
            relief="flat",
            cursor="hand2",
            font=("Segoe UI", 12, "bold"),
            pady=10,
        )


class StartScreen(BaseScreen):
    def __init__(self, app: BattleshipsApp) -> None:
        super().__init__(app)
        self.title_label("BATTLESHIPS", "A classic strategy game for one player")
        emblem = tk.Canvas(self, width=420, height=210, bg="#071a2b", highlightthickness=0)
        emblem.pack(pady=18)
        emblem.create_oval(45, 50, 375, 185, fill="#0b4f71", outline="#167ca5", width=4)
        emblem.create_polygon(95, 130, 330, 130, 292, 165, 125, 165, fill="#7d8b99", outline="white")
        emblem.create_rectangle(175, 92, 260, 130, fill="#7d8b99", outline="white")
        emblem.create_line(214, 92, 214, 55, fill="white", width=4)
        buttons = tk.Frame(self, bg="#071a2b")
        buttons.pack(pady=20)
        self.action(buttons, "New game", app.show_placement).pack(pady=7)
        self.action(buttons, "How to play", app.show_rules).pack(pady=7)
        self.action(buttons, "Exit", app.confirm_exit).pack(pady=7)


class RulesScreen(BaseScreen):
    def __init__(self, app: BattleshipsApp) -> None:
        super().__init__(app)
        self.title_label("HOW TO PLAY")
        rules = (
            "1. Place all five ships on your 10 × 10 grid.\n\n"
            "2. Ships may be horizontal or vertical and cannot overlap.\n\n"
            "3. Select a cell on the opponent's grid to fire.\n\n"
            "4. Red marks are hits; light marks are misses.\n\n"
            "5. The first player to sink the entire opposing fleet wins."
        )
        tk.Label(
            self,
            text=rules,
            justify="left",
            bg=PANEL,
            fg="white",
            font=("Segoe UI", 15),
            padx=45,
            pady=35,
        ).pack(pady=20)
        self.action(self, "Back", app.show_start).pack(pady=22)


class PlacementScreen(BaseScreen):
    def __init__(self, app: BattleshipsApp) -> None:
        super().__init__(app)
        self.fleet: list[Vessel] = []
        self.occupied: set[Cell] = set()
        self.selected_ship: str | None = None
        self.orientation = "H"
        self.buttons: dict[Cell, tk.Button] = {}
        self.ship_buttons: dict[str, tk.Button] = {}
        self.preview_cells: set[Cell] = set()
        self.placement_message = tk.StringVar(
            value="Choose a ship. Horizontal ships extend right; vertical ships extend down."
        )
        self.title_label("PLACE YOUR FLEET", "Select a ship, choose its direction, then select its first cell")

        body = tk.Frame(self, bg="#071a2b")
        body.pack(expand=True, pady=(0, 20))
        board_panel = tk.Frame(body, bg=PANEL, padx=18, pady=18)
        board_panel.grid(row=0, column=0, padx=25)
        self._build_board(board_panel)
        tk.Label(
            board_panel,
            textvariable=self.placement_message,
            wraplength=390,
            justify="center",
            bg=PANEL,
            fg="#b8d8e8",
            font=("Segoe UI", 10, "bold"),
            pady=10,
        ).grid(row=12, column=0, columnspan=11)

        controls = tk.Frame(body, bg=PANEL, padx=28, pady=24)
        controls.grid(row=0, column=1, padx=25, sticky="ns")
        tk.Label(controls, text="Fleet", bg=PANEL, fg="white", font=("Segoe UI", 18, "bold")).pack(pady=(0, 12))
        for name, size in SHIPS.items():
            button = tk.Button(
                controls,
                text=f"{name}  ·  {size}",
                command=lambda ship=name: self.select_ship(ship),
                width=22,
                bg="#1f618d",
                fg="white",
                relief="flat",
                cursor="hand2",
                font=("Segoe UI", 11, "bold"),
                pady=7,
            )
            button.pack(pady=4)
            self.ship_buttons[name] = button
        self.orientation_label = tk.Label(controls, text="Direction: Horizontal", bg=PANEL, fg="#b8d8e8", font=("Segoe UI", 11))
        self.orientation_label.pack(pady=(18, 6))
        self.action(controls, "Rotate", self.rotate).pack(pady=5)
        self.action(controls, "Reset fleet", self.reset).pack(pady=5)
        self.start_button = self.action(controls, "Start battle", self.start_game)
        self.start_button.configure(state="disabled")
        self.start_button.pack(pady=(18, 5))
        tk.Button(controls, text="Main menu", command=app.show_start, bg=PANEL, fg="white", relief="flat", cursor="hand2").pack(pady=8)

    def _build_board(self, parent: tk.Frame) -> None:
        for index in range(GRID_SIZE):
            tk.Label(parent, text=chr(65 + index), bg=PANEL, fg="white", width=3).grid(row=0, column=index + 1)
            tk.Label(parent, text=str(index + 1), bg=PANEL, fg="white", width=3).grid(row=index + 1, column=0)
        for row in range(GRID_SIZE):
            for col in range(GRID_SIZE):
                button = tk.Button(
                    parent,
                    bg=WATER,
                    activebackground=WATER_HOVER,
                    width=3,
                    height=1,
                    relief="ridge",
                    command=lambda r=row, c=col: self.place(r, c),
                )
                button.grid(row=row + 1, column=col + 1)
                button.bind("<Enter>", lambda _event, r=row, c=col: self.show_preview(r, c))
                button.bind("<Leave>", lambda _event: self.clear_preview())
                self.buttons[(row, col)] = button

    def select_ship(self, name: str) -> None:
        self.clear_preview()
        self.selected_ship = name
        for ship_name, button in self.ship_buttons.items():
            button.configure(bg=ACCENT if ship_name == name else "#1f618d", fg="#102a43" if ship_name == name else "white")
        direction = "RIGHT →" if self.orientation == "H" else "DOWN ↓"
        self.placement_message.set(
            f"{name} occupies {SHIPS[name]} cells. Move over the grid to preview it toward {direction}."
        )

    def rotate(self) -> None:
        self.clear_preview()
        self.orientation = "V" if self.orientation == "H" else "H"
        label = "Vertical — extends DOWN ↓" if self.orientation == "V" else "Horizontal — extends RIGHT →"
        self.orientation_label.configure(text=f"Direction: {label}")
        if self.selected_ship:
            self.placement_message.set(
                f"{self.selected_ship} will extend {'DOWN ↓' if self.orientation == 'V' else 'RIGHT →'} from the selected cell."
            )

    def clear_preview(self) -> None:
        for cell in self.preview_cells:
            self.buttons[cell].configure(bg=SHIP if cell in self.occupied else WATER)
        self.preview_cells.clear()

    def show_preview(self, row: int, col: int) -> None:
        self.clear_preview()
        if self.selected_ship is None:
            return
        cells = cells_for(row, col, SHIPS[self.selected_ship], self.orientation)
        visible_cells = {
            cell for cell in cells
            if 0 <= cell[0] < GRID_SIZE and 0 <= cell[1] < GRID_SIZE
        }
        is_valid = valid_cells(cells, self.occupied)
        preview_color = "#2a9d8f" if is_valid else "#e76f51"
        for cell in visible_cells:
            self.buttons[cell].configure(bg=preview_color)
        self.preview_cells = visible_cells
        direction = "right" if self.orientation == "H" else "down"
        if is_valid:
            self.placement_message.set(
                f"Valid position: {self.selected_ship} starts here and extends {direction}. Click to place it."
            )
        elif not cells.isdisjoint(self.occupied):
            self.placement_message.set("Invalid position: the red preview overlaps another ship.")
        else:
            self.placement_message.set("Invalid position: the red preview would leave the grid.")

    def place(self, row: int, col: int) -> None:
        if self.selected_ship is None:
            messagebox.showinfo("Place fleet", "Select a ship first.")
            return
        self.clear_preview()
        size = SHIPS[self.selected_ship]
        cells = cells_for(row, col, size, self.orientation)
        if not valid_cells(cells, self.occupied):
            if not cells.isdisjoint(self.occupied):
                self.placement_message.set("Cannot place ship: it overlaps a ship already on the board.")
            else:
                self.placement_message.set("Cannot place ship: part of it would be outside the board.")
            return
        placed_name = self.selected_ship
        self.fleet.append(Vessel(self.selected_ship, cells))
        self.occupied.update(cells)
        for cell in cells:
            self.buttons[cell].configure(bg=SHIP)
        self.ship_buttons[self.selected_ship].configure(text=f"{self.selected_ship}  ✓", state="disabled", bg="#2d6a4f", fg="white")
        self.selected_ship = None
        self.placement_message.set(f"{placed_name} placed successfully. Choose the next ship.")
        if len(self.fleet) == len(SHIPS):
            self.start_button.configure(state="normal")

    def reset(self) -> None:
        self.fleet.clear()
        self.occupied.clear()
        self.selected_ship = None
        self.clear_preview()
        for button in self.buttons.values():
            button.configure(bg=WATER, state="normal")
        for name, button in self.ship_buttons.items():
            button.configure(text=f"{name}  ·  {SHIPS[name]}", state="normal", bg="#1f618d", fg="white")
        self.start_button.configure(state="disabled")
        self.placement_message.set(
            "Choose a ship. Horizontal ships extend right; vertical ships extend down."
        )

    def start_game(self) -> None:
        self.app.show_game([Vessel(ship.name, set(ship.cells)) for ship in self.fleet])


class GameScreen(BaseScreen):
    def __init__(self, app: BattleshipsApp, player_fleet: list[Vessel]) -> None:
        super().__init__(app)
        self.player_fleet = player_fleet
        self.enemy_fleet = random_fleet()
        self.player_shots: set[Cell] = set()
        self.enemy_shots: set[Cell] = set()
        self.turn_locked = False
        self.game_over = False
        self.pending_after: str | None = None
        self.player_buttons: dict[Cell, tk.Button] = {}
        self.enemy_buttons: dict[Cell, tk.Button] = {}

        self.title_label("BATTLE", "Sink the opposing fleet before it sinks yours")
        self.status = tk.StringVar(value="Your turn — select a cell on the opponent's grid")
        tk.Label(self, textvariable=self.status, bg=ACCENT, fg="#102a43", font=("Segoe UI", 13, "bold"), padx=18, pady=8).pack(pady=(0, 16))

        boards = tk.Frame(self, bg="#071a2b")
        boards.pack(expand=True)
        self._create_board(boards, "YOUR FLEET", self.player_buttons, 0, False)
        self._create_board(boards, "OPPONENT", self.enemy_buttons, 1, True)
        footer = tk.Frame(self, bg="#071a2b")
        footer.pack(pady=24)
        self.action(footer, "Restart", app.show_placement, 16).pack(side="left", padx=8)
        self.action(footer, "Main menu", app.show_start, 16).pack(side="left", padx=8)
        self._paint_player_ships()

    def destroy(self) -> None:
        if self.pending_after is not None:
            try:
                self.after_cancel(self.pending_after)
            except tk.TclError:
                pass
        super().destroy()

    def _create_board(self, parent: tk.Frame, title: str, target: dict[Cell, tk.Button], column: int, clickable: bool) -> None:
        panel = tk.Frame(parent, bg=PANEL, padx=18, pady=18)
        panel.grid(row=0, column=column, padx=24)
        tk.Label(panel, text=title, bg=PANEL, fg="white", font=("Segoe UI", 16, "bold")).grid(row=0, column=0, columnspan=11, pady=(0, 10))
        for index in range(GRID_SIZE):
            tk.Label(panel, text=chr(65 + index), bg=PANEL, fg="white", width=3).grid(row=1, column=index + 1)
            tk.Label(panel, text=str(index + 1), bg=PANEL, fg="white", width=3).grid(row=index + 2, column=0)
        for row in range(GRID_SIZE):
            for col in range(GRID_SIZE):
                command = (lambda r=row, c=col: self.fire(r, c)) if clickable else None
                button = tk.Button(panel, bg=WATER, activebackground=WATER_HOVER, width=3, height=1, relief="ridge", command=command)
                button.grid(row=row + 2, column=col + 1)
                target[(row, col)] = button

    def _paint_player_ships(self) -> None:
        for ship in self.player_fleet:
            for cell in ship.cells:
                self.player_buttons[cell].configure(bg=SHIP)

    @staticmethod
    def vessel_at(fleet: list[Vessel], cell: Cell) -> Vessel | None:
        return next((ship for ship in fleet if cell in ship.cells), None)

    @staticmethod
    def fleet_sunk(fleet: list[Vessel], shots: set[Cell]) -> bool:
        return all(ship.is_sunk(shots) for ship in fleet)

    def mark_shot(self, buttons: dict[Cell, tk.Button], cell: Cell, hit: bool, sunk_ship: Vessel | None = None) -> None:
        button = buttons[cell]
        button.configure(text="×" if hit else "•", fg="white" if hit else "#102a43", bg=HIT if hit else MISS, state="disabled", disabledforeground="white" if hit else "#102a43")
        if sunk_ship is not None:
            for ship_cell in sunk_ship.cells:
                buttons[ship_cell].configure(bg=SUNK, fg="white", disabledforeground="white")

    def fire(self, row: int, col: int) -> None:
        cell = (row, col)
        if self.game_over or self.turn_locked or cell in self.player_shots:
            return
        self.turn_locked = True
        self.player_shots.add(cell)
        ship = self.vessel_at(self.enemy_fleet, cell)
        sunk = ship if ship and ship.is_sunk(self.player_shots) else None
        self.mark_shot(self.enemy_buttons, cell, ship is not None, sunk)
        if self.fleet_sunk(self.enemy_fleet, self.player_shots):
            self.finish(True)
            return
        if sunk:
            self.status.set(f"You sank the opponent's {sunk.name}. Opponent's turn…")
        else:
            self.status.set("Hit! Opponent's turn…" if ship else "Miss. Opponent's turn…")
        # Keep the result visible long enough to be read before the opponent fires.
        self.pending_after = self.after(2000, self.computer_turn)

    def computer_turn(self) -> None:
        self.pending_after = None
        if self.game_over:
            return
        available = [(row, col) for row in range(GRID_SIZE) for col in range(GRID_SIZE) if (row, col) not in self.enemy_shots]
        cell = random.choice(available)
        self.enemy_shots.add(cell)
        ship = self.vessel_at(self.player_fleet, cell)
        sunk = ship if ship and ship.is_sunk(self.enemy_shots) else None
        self.mark_shot(self.player_buttons, cell, ship is not None, sunk)
        if self.fleet_sunk(self.player_fleet, self.enemy_shots):
            self.finish(False)
            return
        if sunk:
            self.status.set(f"The opponent sank your {sunk.name}. Your turn.")
        else:
            self.status.set("The opponent hit your ship. Your turn." if ship else "The opponent missed. Your turn.")
        self.turn_locked = False

    def finish(self, player_won: bool) -> None:
        self.game_over = True
        self.turn_locked = True
        message = "Victory! You sank the opposing fleet." if player_won else "Defeat. The opponent sank your fleet."
        self.status.set(message)
        for button in self.enemy_buttons.values():
            button.configure(state="disabled")
        messagebox.showinfo("Game over", message)


if __name__ == "__main__":
    BattleshipsApp().mainloop()
