#!/usr/bin/env python
import setup_paths
import re
import sys
import os
import logging
import json
from nomadcore.match_highlighter import ANSI

LOGGER = logging.getLogger(__name__)


class TokenMatchError(Exception):
    pass


class token(object):
    highlight_start = ''
    highlight_end = ANSI.RESET
    regex = None
    cRE_end_newline = re.compile(r'(.*?)(\n*)$')

    def __init__(self, line, pos_in_line):
        """token constructor takes re.match object as arg"""
        self.match = self.regex.match(line, pos_in_line)
        if self.match is None:
            raise TokenMatchError
        self.value_str = self.match.group(0)
        self.value = self.match2value()

    def highlighted(self):
        """return ANSI-highlighted token"""
        m = self.cRE_end_newline.match(self.value_str)
        return self.highlight_start + m.group(1) + self.highlight_end + m.group(2)

    def match2value(self):
        return None

    def __str__(self):
        return "%10s %s" % (self.__class__.__name__, str(self.value))


class token_literal(token):
    regex = re.compile(
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

    def match2value(self):
        match = self.match
        if match.group('str_d') is not None:
            return match.group('str_d')
        if match.group('str_s') is not None:
            return match.group('str_s')
        if match.group('float') is not None:
            return float(match.group('float'))
        if match.group('hex_int') is not None:
            return int(match.group('hex_int'), base=16)
        if match.group('octal_int') is not None:
            return int(match.group('octal_int'), base=8)
        if match.group('decimal_int') is not None:
            return int(match.group('decimal_int'))
        if match.group('logical') is not None:
            if match.group('logical') == 't':
                return True
            else:
                return False
        raise RuntimeError('no idea what to do with literal "%s"' % (match.group(0)))


class token_datatype(token):
    regex = re.compile(r'\s*([a-zA-Z_][a-zA-Z0-9_]*)')
    subtype_list = []
    subtype_dict = {}

    def match2value(self):
        value = self.subtype_dict.get(self.match.group(1), None)
        if value is None:
            raise TokenMatchError
        return value

    def __str__(self):
        return "%10s %s" % (self.__class__.__name__, str(self.subtype_list[self.value]))

token_datatype.subtype_list = [
        'char',
        'int',
        'real',
        'logical',
        'flag',
    ]

token_datatype.subtype_dict = { token_datatype.subtype_list[i]: i for i in range(len(token_datatype.subtype_list)) }


class token_keyword(token):
    regex = re.compile(r'\s*([a-zA-Z_][a-zA-Z0-9_]*)')
    subtype_list = []
    subtype_dict = {}

    def match2value(self):
        value = self.subtype_dict.get(self.match.group(1), None)
        if value is None:
            raise TokenMatchError
        return value

    def __str__(self):
        return "%10s %s" % (self.__class__.__name__, str(self.subtype_list[self.value]))

token_keyword.subtype_list = [
        'section',
        'struct',
    ]

token_keyword.subtype_dict = { token_keyword.subtype_list[i]: i for i in range(len(token_keyword.subtype_list)) }


class token_identifier(token):
    regex = re.compile(r'\s*([a-zA-Z_][a-zA-Z0-9_]*)')

    def match2value(self):
        return self.match.group(1)


class token_subscript_begin(token):
    regex = re.compile(r'\[')


class token_subscript_end(token):
    regex = re.compile(r'\]')


class token_operator(token):
    regex = re.compile(r'\s*(\+=|\-=|=|,|-|\+|/|\*)')

    def match2value(self):
        return self.match.group(1)


class token_block_begin(token):
    regex = re.compile(r'\s*\{')


class token_block_end(token):
    regex = re.compile(r'\s*\}')


class token_statement_end(token):
    regex = re.compile(r'\s*;')


class token_line_comment(token):
    regex = re.compile(r'\s*(?:(//|#)|(/\*))(?P<comment>.*)')

    def match2value(self):
        return self.match.group('comment')

class token_trailing_whitespace(token):
    regex = re.compile(r'\s+$')

class token_bad_input(token):
    regex = re.compile('(.+)$')

    def match2value(self):
        return self.match.group(1)

class token_flag_value(token):
    regex = re.compile(r'\(([+-])\)')

    def match2value(self):
        if self.match.group(1) == '+':
            return True
        else:
            return False


token_literal.highlight_start = ANSI.FG_MAGENTA
token_datatype.highlight_start = ANSI.FG_YELLOW
token_keyword.highlight_start = ANSI.FG_BRIGHT_YELLOW
token_identifier.highlight_start = ANSI.FG_CYAN
token_subscript_begin.highlight_start = ANSI.FG_BRIGHT_GREEN
token_subscript_end.highlight_start = ANSI.FG_BRIGHT_GREEN
token_operator.highlight_start = ANSI.FG_RED
token_block_begin.highlight_start = ANSI.FG_BRIGHT_CYAN
token_block_end.highlight_start = ANSI.FG_BRIGHT_CYAN
token_statement_end.highlight_start = ANSI.FG_BRIGHT_YELLOW
token_line_comment.highlight_start = ANSI.FG_BLUE
token_trailing_whitespace.highlight_start = ANSI.BG_BLUE
token_bad_input.highlight_start = ANSI.BEGIN_INVERT + ANSI.FG_BRIGHT_RED
token_flag_value.highlight_start = ANSI.FG_MAGENTA


class syntax_node(object):
    def __init__(self, parent):
        self.items = []
        # backref
        self.parent = parent

    def append(self, item):
        self.items.append(item)

    def indented_dump(self, indent):
        if len(self.items) < 1:
            return ''
        result = indent + self.__class__.__name__ + ":\n"
        for item in self.items:
            if isinstance(item, syntax_node):
                result = result + item.indented_dump(indent + '  ')
            else:
                result = result + indent + '  ' + str(item) + '\n'
        return result

    def nomadmetainfo(self, prefix):
        pass


class statement(syntax_node):
    def nomadmetainfo(self, prefix, indent):
        if len(self.items) < 1:
            return None
        if isinstance(self.items[0], token_keyword):
            if self.items[0].value == 0:
                # section
                secname = prefix + '.' + self.items[1].value
                sys.stderr.write("%ssection %s\n" % (indent, secname))
                if isinstance(self.items[2], block):
                    self.items[2].nomadmetainfo(secname, indent + '  ')
                else:
                    raise Exception("No block for %s" % (indent + '  '))
            elif self.items[0].value == 1:
                structname = prefix + '.' + self.items[2].value
                if len(self.items) > 3 and isinstance(self.items[3], subscript):
                    struct_subscript = str(self.items[3])
                else:
                    struct_subscript = ''
                # struct
                sys.stderr.write("%sstruct %s%s\n" % (indent, structname, struct_subscript))
                if isinstance(self.items[1], block):
                    self.items[1].nomadmetainfo(structname, indent + '  ')
                else:
                    sys.stderr.write("%s NOBLOCK" % (indent + '  '))
        elif isinstance(self.items[0], token_datatype):
            sys.stderr.write("%s%s\n" % (indent + '  ', self.items[0].subtype_list[self.items[0].value]))
        else:
            LOGGER.error("no idea what to do with statement starting with %s", str(self.items[0]))



class block(syntax_node):
    def nomadmetainfo(self, prefix, indent):
        if len(self.items) < 1:
            return None
        for item in self.items:
            item.nomadmetainfo(prefix, indent)


class subscript(statement):
    def __str__(self):
        result = '['
        for item in self.items:
            result = result + item.value
        result = result + ']'
        return result


class FploInputParser(object):
    """Parser for C-like FPLO input
    """
    def __init__(self, file_path, annotateFile = None):
        self.input_tree = {}
        self.file_path = file_path
        self.state = self.state_root
        self.__annotateFile = annotateFile
        self.bad_input = False
        # start with root block, and add empty statement to append to
        self.statements = block(None)
        self.statements.append(statement(self.statements))
        self.statement = self.statements.items[-1]

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

    def _annotate(self, what):
        """write string to annotateFile if present"""
        if self.__annotateFile:
            self.__annotateFile.write(what)

    def state_root(self, line, pos_in_line):
        """state: no open section, i.e. at the root of the namelist"""
        this_token = None
        for try_token in [token_literal, token_flag_value, token_datatype,
                          token_keyword,
                          token_identifier, token_subscript_begin,
                          token_subscript_end, token_operator,
                          token_block_begin, token_block_end,
                          token_statement_end, token_line_comment,
                          token_trailing_whitespace,
                          token_bad_input,
                          ]:
            try:
                this_token = try_token(line, pos_in_line)
            except TokenMatchError:
                pass
            if this_token is not None:
                break
        if this_token is not None:
            self._annotate(this_token.highlighted())
            # LOGGER.error('cls: %s', this_token.__class__.__name__)
            if isinstance(this_token, token_block_begin):
                newblock = block(self.statement)
                newblock.append(statement(newblock))
                self.statement.append(newblock)
                self.statement = newblock.items[0]
            elif isinstance(this_token, token_block_end):
                self.statement = self.statement.parent.parent
            elif isinstance(this_token, token_subscript_begin):
                newsubscript = subscript(self.statement)
                self.statement.append(newsubscript)
                self.statement = newsubscript
            elif isinstance(this_token, token_subscript_end):
                self.statement = self.statement.parent
            elif isinstance(this_token, token_statement_end):
                self.statement.parent.append(statement(self.statement.parent))
                self.statement = self.statement.parent.items[-1]
            elif isinstance(this_token, token_bad_input):
                self.bad_input = True
            elif isinstance(this_token, (token_line_comment, token_trailing_whitespace)):
                pass
            else:
                self.statement.append(this_token)
            return this_token.match.end()
        return None

    def onBad_input(self):
        """hook: called at the end of parsing if there was any bad input"""
        pass

    def onEnd_of_file(self):
        """hook: called at the end of parsing"""
        sys.stdout.flush()
        sys.stderr.flush()
        # sys.stderr.write(self.statements.indented_dump('')) # json.dumps(self.statements, sort_keys=True, indent=4, separators=(',', ': ')))
        self.statements.nomadmetainfo('x_fplo_in','')

if __name__ == "__main__":
    parser = FploInputParser(sys.argv[1], annotateFile=sys.stdout)
    parser.parse()
