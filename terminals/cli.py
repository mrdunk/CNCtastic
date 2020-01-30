# pylint: disable=E1101  # Module 'curses' has no 'XXXX' member (no-member)

""" Plugin to provide command line IO using curses library. """

from typing import Optional, Any, Union

import atexit
from io import StringIO
import sys
import os
import curses

from terminals._terminalBase import _TerminalBase

class_name = "Cli"

class Cli(_TerminalBase):
    """ Plugin to provide command line IO using curses library. """

    # pylint: disable=W0613
    def __init__(self, label: str = "cli") -> None:
        super().__init__(label)
        self._setup_done: bool = False
        self.active_by_default = False
        self.description = "CLI interface for console operation."

    def setup(self) -> None:
        """ Configuration to be done after class instantiation. """
        self._setup_done = True
        os.environ.setdefault('ESCDELAY', '25')

        # Replace default stdout (terminal) with a stream so it doesn't mess with
        # curses.
        self.temp_stdout = StringIO()
        sys.stdout = self.temp_stdout
        self.temp_stdout_pos = 0

        # Undo curses stuff in the event of a crash.
        atexit.register(self.close)

        self.stdscr = curses.initscr()
        if curses.has_colors():
            curses.start_color()
            curses.init_pair(1, curses.COLOR_RED, curses.COLOR_WHITE)
        curses.noecho()
        curses.cbreak()
        self.stdscr.keypad(True)
        self.stdscr.nodelay(True)
        self.stdscr.clear()

        begin_x = 0
        begin_y = 0
        height = curses.LINES
        width = int(curses.COLS / 2)
        self.win_main_border = self.stdscr.subwin(height, width, begin_y, begin_x)
        self.win_main_border.border()
        self.win_mainout = curses.newwin(height - 2, width - 2, begin_y + 1, begin_x + 1)
        self.win_mainout.scrollok(True)

        begin_x = int(curses.COLS / 2)
        begin_y = 0
        self.win_stdout_border = self.stdscr.subwin(height, width, begin_y, begin_x)
        self.win_stdout_border.border()
        self.win_stdout = curses.newwin(height - 2, width - 2, begin_y + 1, begin_x + 1)
        self.win_stdout.scrollok(True)

        #self.stdscr.addstr(2,2,"hello")
        #self.stdscr.addstr(10,10,"world", curses.A_REVERSE)
        #if curses.has_colors():
        #    self.stdscr.addstr(3,3,"Pretty text", curses.color_pair(1))

        self.stdscr.refresh()
        self.win_yes_no: Optional[Any] = None

    def yesno(self, message: str = "") -> None:
        """ Display confirmation window. """
        if message:
            begin_x = int(curses.COLS / 2 - 10)
            begin_y = int(curses.LINES / 2 - 3)
            height = 6
            width = 20
            self.win_yes_no = curses.newwin(height, width, begin_y, begin_x)
            self.win_yes_no.clear()
            self.win_yes_no.border()
            self.win_yes_no.addstr(2, 2, message)
            self.win_yes_no.refresh()
        else:
            del self.win_yes_no
            self.win_yes_no = None
            self.win_mainout.touchwin()
            self.win_stdout.touchwin()
            self.win_main_border.refresh()
            self.win_stdout_border.refresh()
            self.win_mainout.refresh()
            self.win_stdout.refresh()

    def early_update(self) -> bool:
        """ To be called once per frame.
        Returns:
            bool: True: Continue execution.
                  False: An "Exit" or empty event occurred. Stop execution. """
        if not self._setup_done:
            return True

        character: Union[str, bytes, int, None] = None
            
        #character = self.stdscr.getkey()   # read a keypress
        character = self.stdscr.getch()   # read a keypress

        if character is not None and isinstance(character, int) and character > -1:
            self.win_mainout.addstr("%s %s\n" % (character, curses.keyname(character)))
            self.win_mainout.refresh()

        if self.temp_stdout.tell() > self.temp_stdout_pos:
            self.temp_stdout.seek(self.temp_stdout_pos)
            val = self.temp_stdout.read()
            self.temp_stdout_pos = self.temp_stdout.tell()

            self.win_stdout.addstr(val)
            self.win_stdout.refresh()

        if self.win_yes_no:
            if character == 27:   # Esc
                # Cancel yesno.
                self.yesno()
            elif character == 10:  # Enter
                # Quit.
                return False
        elif character == 27:
            # Enable yesno.
            self.yesno("Enter to quit.")

        return True

    def close(self) -> None:
        """ Close curses session, restore shell settings. """
        if not self._setup_done:
            return

        curses.nocbreak()
        self.stdscr.keypad(False)
        curses.echo()
        #input()
        curses.endwin()

        # Replace stdout
        sys.stdout = sys.__stdout__
        #sys.stdout.write(self.temp_stdout.getvalue())

        self._setup_done = False
