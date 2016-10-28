#!/usr/bin/env python
import setup_paths
import re
import sys
import os
import logging
import json
from nomadcore.match_highlighter import ANSI

LOGGER = logging.getLogger(__name__)


cRE_end_newline = re.compile(r'(.*?)(\n*)$')

# keywords/identifiers
cRE_kw_ident = re.compile(r'\s*([a-zA-Z_][a-zA-Z0-9_]*)')
# comments
cRE_comment = re.compile(r'\s*(?:(//|#)|(/\*))(?P<comment>.*)')

cRE_trailing_whitespace = re.compile(r'\s+$')

cRE_opening_brace = re.compile(r'\s*\{')
cRE_closing_brace = re.compile(r'\s*\}')
cRE_end_statement = re.compile(r'\s*;')

cRE_subscript = re.compile(r'\[([^\]]*)\]')

cRE_operator = re.compile(r'\s*(\+=|\-=|=|,|-|\+|/|\*)')

cRE_literal = re.compile(
    r'\s*' + r'(?:' + r'|'.join([
        # alternates for literals
        # RE_f,
        r'"(?P<str_d>[^"\\]*(?:\\\\|\\"|[^"]*)*)"',
        r"'(?P<str_s>[^'\\]*(?:\\\\|\\'|[^']*)*)'",
        r'(?P<float>' + (
            r'[+-]?' + # optional sign
            r'\d+(?=[\.eE])' + # positive lookahead: either decimal point or exponential part must follow
            r'(?:\.\d*)?' + #cover decimals if present
            r'(?:[eE][+-]\d+)?' # exponential part if present
        r')'),
        r'0x(?P<hex_int>[0-9a-fA-F]+)',
        r'0(?P<octal_int>[0-7]+)',
        r'(?P<decimal_int>[+-]?\d+)', # integer with optional sign
        r'(?P<logical>[tf])(?=\W)',
    ]) + r')'
)

class FploInputParser(object):
    """Parser for C-like FPLO input
    """
    def __init__(self, file_path, annotateFile = None):
        self.input_tree = {}
        self.file_path = file_path
        self.state = self.state_root
        self.__annotateFile = annotateFile
        self.__cre_closing = None
        self.bad_input = False
        self.statements = [[]]
        self.parent_stack = [self.statements]
        self.statement = self.statements[-1]

    def parse(self):
        """open file and parse line-by-line"""
        with open(self.file_path, "r") as fIn:
            # process line-by-line
            for line in fIn:
                self.parse_line(line)
        # check if there was input flagged as 'bad'/'syntactically incorrect'
        if self.bad_input:
            # call bad-input hook
            self.onBad_input()
        # call end-of-file hook
        self.onEnd_of_file()

    def parse_line(self, line):
        """parse one line, delegating to the parser state handlers"""
        pos_in_line = 0
        while pos_in_line<len(line):
            new_pos_in_line = self.state(line, pos_in_line)
            # check if anything was parsed, otherwise cancel that line
            if new_pos_in_line is None:
                break
            else:
                pos_in_line = new_pos_in_line
        if pos_in_line < len(line):
            self.bad_input = True
            self.annotate(line[pos_in_line:], ANSI.BEGIN_INVERT + ANSI.FG_BRIGHT_RED)

    def annotate(self, what, highlight):
        """write string to annotateFile with ANSI highlight/reset sequences"""
        if self.__annotateFile:
            m = cRE_end_newline.match(what)
            self.__annotateFile.write(highlight + m.group(1) + ANSI.RESET + m.group(2))

    def state_root(self, line, pos_in_line):
        """state: no open section, i.e. at the root of the namelist"""
        # match literals
        m = cRE_literal.match(line, pos_in_line)
        if m is not None:
            self.annotate(m.group(), ANSI.FG_MAGENTA)
            return m.end()
        # match identifier or keyword
        m = cRE_kw_ident.match(line, pos_in_line)
        if m is not None:
            self.annotate(m.group(), ANSI.FG_BRIGHT_GREEN)
            self.statement.append(m.group(1))
            return m.end()
        # match subscript of previous identifier
        m = cRE_subscript.match(line, pos_in_line)
        if m is not None:
            self.annotate(m.group(), ANSI.FG_GREEN)
            return m.end()
        # match operators
        m = cRE_operator.match(line, pos_in_line)
        if m is not None:
            self.annotate(m.group(), ANSI.FG_YELLOW)
            return m.end()
        # match block-open
        m = cRE_opening_brace.match(line, pos_in_line)
        if m is not None:
            self.annotate(m.group(), ANSI.FG_BRIGHT_CYAN)
            self.parent_stack.append(self.statement)
            self.statement.append([])
            self.statement = self.statement[-1]
            return m.end()
        # match block-close
        m = cRE_closing_brace.match(line, pos_in_line)
        if m is not None:
            self.statement = self.parent_stack.pop()
            self.annotate(m.group(), ANSI.FG_BRIGHT_CYAN)
            return m.end()
        # match statement-finishing semicolon
        m = cRE_end_statement.match(line, pos_in_line)
        if m is not None:
            self.statement = []
            self.parent_stack[-1].append(self.statement)
            self.annotate(m.group(), ANSI.FG_BRIGHT_YELLOW)
            return m.end()
        # match up-to-eol comments
        m = cRE_comment.match(line, pos_in_line)
        if m is not None:
            self.annotate(m.group(), ANSI.FG_BLUE)
            # self.onComment(m.group('comment'))
            return m.end()
        # ignore remaining whitespace
        m = cRE_trailing_whitespace.match(line, pos_in_line)
        if m is not None:
            self.annotate(m.group(), ANSI.BG_BLUE)
            return m.end()
        # # nothing matched, call hook
        # return self.onRoot_data(line, pos_in_line)

    def onRoot_data(self, line, pos_in_line):
        """hook: called if data appears outside namelists groups, directly
        at root level within the file;
        data means: line is not empty or a comment
        useful for code-specific extensions beyond the F90 namelist standard
        """
        return None

    def onBad_input(self):
        """hook: called at the end of parsing if there was any bad input"""
        pass

    def onEnd_of_file(self):
        """hook: called at the end of parsing"""
        sys.stdout.flush()
        sys.stderr.flush()
        sys.stderr.write(json.dumps(self.statements, sort_keys=True, indent=4, separators=(',', ': ')))

if __name__ == "__main__":
    parser = FploInputParser(sys.argv[1], annotateFile=sys.stdout)
    parser.parse()
