""" Plugin to provide command line IO using curses library. """

from typing import List, Optional, Any, Union

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
        self.tempStdout = StringIO()
        sys.stdout = self.tempStdout
        self.tempStdoutPos = 0

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
        self.winMainBorder = self.stdscr.subwin(height, width, begin_y, begin_x)
        self.winMainBorder.border()
        self.winMainout = curses.newwin(height - 2, width - 2, begin_y + 1, begin_x + 1)
        self.winMainout.scrollok(True)

        begin_x = int(curses.COLS / 2)
        begin_y = 0
        self.winStdoutBorder = self.stdscr.subwin(height, width, begin_y, begin_x)
        self.winStdoutBorder.border()
        self.winStdout = curses.newwin(height - 2, width - 2, begin_y + 1, begin_x + 1)
        self.winStdout.scrollok(True)

        #self.stdscr.addstr(2,2,"hello")
        #self.stdscr.addstr(10,10,"world", curses.A_REVERSE)
        #if curses.has_colors():
        #    self.stdscr.addstr(3,3,"Pretty text", curses.color_pair(1))

        self.stdscr.refresh()
        self.winYesNo: Optional[Any] = None

    def yesno(self, message: str = "") -> None:
        """ Display confirmation window. """
        if message:
            begin_x = int(curses.COLS / 2 - 10)
            begin_y = int(curses.LINES / 2 - 3)
            height = 6
            width = 20
            self.winYesNo = curses.newwin(height, width, begin_y, begin_x)
            self.winYesNo.clear()
            self.winYesNo.border()
            self.winYesNo.addstr(2, 2, message)
            self.winYesNo.refresh()
        else:
            del self.winYesNo
            self.winYesNo = None
            self.winMainout.touchwin()
            self.winStdout.touchwin()
            self.winMainBorder.refresh()
            self.winStdoutBorder.refresh()
            self.winMainout.refresh()
            self.winStdout.refresh()

    def early_update(self) -> bool:
        """ To be called once per frame.
        Returns:
            bool: True: Continue execution.
                  False: An "Exit" or empty event occurred. Stop execution. """
        if not self._setup_done:
            return True

        character: Union[str, bytes, int, None] = None
        try:
            #character = self.stdscr.getkey()   # read a keypress
            character = self.stdscr.getch()   # read a keypress
        except:
            pass
        if character is not None and isinstance(character, int) and character > -1:
            self.winMainout.addstr("%s %s\n" % (character, curses.keyname(character)))
            self.winMainout.refresh()

        if self.tempStdout.tell() > self.tempStdoutPos:
            self.tempStdout.seek(self.tempStdoutPos)
            val = self.tempStdout.read()
            self.tempStdoutPos = self.tempStdout.tell()

            self.winStdout.addstr(val)
            self.winStdout.refresh()

        if self.winYesNo:
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
        #sys.stdout.write(self.tempStdout.getvalue())

        self._setup_done = False
