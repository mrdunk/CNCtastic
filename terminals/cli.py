from typing import List, Dict, Optional, Any, Union

import atexit
from io import StringIO
import sys
import os
import curses

from terminals._terminalBase import _TerminalBase, diffDicts

className = "Cli"

class Cli(_TerminalBase):
    def __init__(self, layouts: List=[], label: str="cli") -> None:
        super().__init__(label)
        self.setupDone: bool = False
        self.activeByDefault = False
        self.description = "CLI interface for console operation."

    def setup(self) -> None:
        self.setupDone = True
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

        begin_x = 0; begin_y = 0
        height = curses.LINES; width = int(curses.COLS / 2)
        self.winMainBorder = self.stdscr.subwin(height, width, begin_y, begin_x)
        self.winMainBorder.border()
        self.winMainout = curses.newwin(height - 2, width - 2, begin_y + 1, begin_x + 1)
        self.winMainout.scrollok(True)

        begin_x = int(curses.COLS / 2); begin_y = 0
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

    def yesNo(self, message: str="") -> None:
        if message:
            begin_x = int(curses.COLS / 2 - 10); begin_y = int(curses.LINES / 2 - 3)
            height = 6; width = 20
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
    
    def earlyUpdate(self) -> bool:
        """ To be called once per frame.
        Returns:
            bool: True: Continue execution.
                  False: An "Exit" or empty event occurred. Stop execution. """
        if not self.setupDone:
            return True
        
        c: Union[str, bytes, int, None] = None
        try:
            #c = self.stdscr.getkey()   # read a keypress
            c = self.stdscr.getch()   # read a keypress
        except:
            pass
        if c is not None and isinstance(c, int) and c > -1:
            self.winMainout.addstr("%s %s\n" % (c, curses.keyname(c)))
            self.winMainout.refresh()

        if self.tempStdout.tell() > self.tempStdoutPos:
            self.tempStdout.seek(self.tempStdoutPos)
            val = self.tempStdout.read()
            self.tempStdoutPos = self.tempStdout.tell()

            self.winStdout.addstr(val)
            self.winStdout.refresh()

        if self.winYesNo:
            if c == 27:   # Esc
                # Cancel yesNo.
                self.yesNo()
            elif c == 10:  # Enter
                # Quit.
                return False
        elif c == 27:
            # Enable yesNo.
            self.yesNo("Enter to quit.")

        return True

    def close(self) -> None:
        if not self.setupDone:
            return

        curses.nocbreak()
        self.stdscr.keypad(False)
        curses.echo()
        #input()
        curses.endwin()

        # Replace stdout
        sys.stdout = sys.__stdout__
        #sys.stdout.write(self.tempStdout.getvalue())

        self.setupDone = False


