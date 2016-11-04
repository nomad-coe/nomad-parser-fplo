#!/usr/bin/env python
"""FPLO uses C-inspired input files. They are not quite C, so no conventional
C parser library can be used.
Among the more complex features are nested structs, as well
as arrays-of-struct.

This module is implemented as follows:
1) tokenizer for the used C subset/dialect
2) transformation of tokenized output to concrete syntax tree
3) transformation of concrete syntax tree to abstract syntax tree (AST)
TODO:
4) transform AST to metaInfo backend calls
"""
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
        return str(self.value)

    def __repr__(self):
        return "%10s %s" % (self.__class__.__name__, repr(self.value))


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
        value_index = self.subtype_dict.get(self.match.group(1), None)
        if value_index is None:
            raise TokenMatchError
        self.value_index = value_index
        value = self.subtype_list[value_index]
        return value

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
        value_index = self.subtype_dict.get(self.match.group(1), None)
        if value_index is None:
            raise TokenMatchError
        self.value_index = value_index
        value = self.subtype_list[value_index]
        return value

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
token_operator.highlight_start = ANSI.BEGIN_INVERT + ANSI.FG_YELLOW
token_block_begin.highlight_start = ANSI.FG_BRIGHT_CYAN
token_block_end.highlight_start = ANSI.FG_BRIGHT_CYAN
token_statement_end.highlight_start = ANSI.FG_BRIGHT_YELLOW
token_line_comment.highlight_start = ANSI.FG_BLUE
token_trailing_whitespace.highlight_start = ANSI.BG_BLUE
token_bad_input.highlight_start = ANSI.BEGIN_INVERT + ANSI.FG_BRIGHT_RED
token_flag_value.highlight_start = ANSI.FG_MAGENTA


class AST_node(dict):
    """base class for abstract syntax tree nodes"""
    def __init__(self, name=None):
        self.name = name
        self.child = []

    def indented_str(self, indent=''):
        result = ANSI.BG_YELLOW + indent + ANSI.RESET + ('%-20s' % (self.__class__.__name__))
        if self.name is not None:
            result = result + ' ' + self.name
        result = result + '\n'
        child_indent = indent + '  '
        for child in self.child:
            if child is not None:
                result = result + child.indented_str(child_indent)
        return result

    def append(self, newchild):
        self.child.append(newchild)

    def __len__(self):
        return len(self.child)


class AST_block(AST_node):
    """generic block (sequence of statements) in AST"""
    def append_block(self, src_block):
        for src_child in src_block.child:
            self.append(src_child)


class AST_section(AST_block):
    """section block (sequence of statements) in AST"""
    pass


class AST_datatype(AST_node):
    pass


class AST_datatype_primitive(AST_datatype):
    pass


class AST_datatype_struct(AST_datatype):
    def append_block(self, src_block):
        for src_child in src_block.child:
            self.append(src_child)

class AST_datatype_flag(AST_datatype_struct):
    pass


class AST_declaration(AST_node):
    """variable declaration in abstract syntax tree"""
    # children:
    #   0 - shape
    #   1 - datatype
    def __init__(self, name, datatype, shape=None):
        AST_node.__init__(self, name)
        self.child.append(shape)
        self.child.append(datatype)

    def set_shape(self, shape):
        if self.child[0] is not None:
            raise RuntimeError('already has shape: %s', self.name)
        self.child[0] = shape


class AST_shape(AST_node):
    # children are ints without indented_str method
    def indented_str(self, indent=''):
        result = ANSI.BG_YELLOW + indent + ANSI.RESET + ('%-20s [' % (self.__class__.__name__))
        result = result + ', '.join(map(str, self.child))
        result = result + ']\n'
        return result


class AST_value(AST_node):
    pass


class AST_value_primitive(AST_value):
    # there is one child, a python literal
    def indented_str(self, indent=''):
        result = ANSI.BG_YELLOW + indent + ANSI.RESET + (
            '%-20s %s\n' % (self.__class__.__name__, str(self.child[0])))
        return result


class AST_value_list(AST_value):
    def indented_str(self, indent=''):
        result = ANSI.BG_YELLOW + indent + ANSI.RESET + (
            '%-20s %s\n' % (self.__class__.__name__, repr(self.child)))
        return result


class AST_assignment(AST_node):
    # children:
    # 0: target (type AST_declaration)
    # 1: value (type AST_value)
    pass


class concrete_node(object):
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
            if isinstance(item, concrete_node):
                result = result + item.indented_dump(indent + '  ')
            else:
                result = result + indent + '  ' + str(item) + '\n'
        return result

    def nomadmetainfo(self, prefix):
        pass

    def to_AST(self):
        raise Exception("unimplemented to_AST in %s" % (self.__class__.__name__))


class concrete_statement(concrete_node):
    def nomadmetainfo(self, prefix, indent):
        if len(self.items) < 1:
            return None
        if isinstance(self.items[0], token_keyword):
            if self.items[0].value == 'section':
                # section
                secname = prefix + '.' + self.items[1].value
                sys.stderr.write("%ssection %s\n" % (indent, secname))
                if isinstance(self.items[2], concrete_block):
                    self.items[2].nomadmetainfo(secname, indent + '  ')
                else:
                    raise Exception("No block for %s" % (indent + '  '))
            elif self.items[0].value == 'struct':
                structname = prefix + '.' + self.items[2].value
                if len(self.items) > 3 and isinstance(self.items[3], concrete_subscript):
                    struct_subscript = str(self.items[3])
                else:
                    struct_subscript = ''
                # struct
                sys.stderr.write("%sstruct %s%s\n" % (indent, structname, struct_subscript))
                if isinstance(self.items[1], concrete_block):
                    self.items[1].nomadmetainfo(structname, indent + '  ')
                else:
                    sys.stderr.write("%s NOBLOCK" % (indent + '  '))
        elif isinstance(self.items[0], token_datatype):
            sys.stderr.write("%s%s\n" % (indent + '  ', self.items[0].value))
        else:
            LOGGER.error("no idea what to do with statement starting with %s", str(self.items[0]))

    def to_AST(self):
        if len(self.items) < 1:
            return None
        result = None
        pos_in_statement = 0
        # check declarations
        if isinstance(self.items[0], token_keyword):
            if self.items[0].value == 'section':
                result = AST_section(self.items[1].value) # name of section
                result.append_block(self.items[2].to_AST()) # section-block
                pos_in_statement = 3
            if self.items[0].value == 'struct':
                struct = AST_datatype_struct()
                struct.append_block(self.items[1].to_AST())
                result = AST_declaration(self.items[2].value, struct)
                pos_in_statement = 3
        elif isinstance(self.items[0], token_datatype) and self.items[0].value == 'flag':
            # special case for non-C-primtype 'flag'
            #   we will map this to struct of logicals, but need to evaluate
            #   RHS to get the names. messy.
            flag = AST_datatype_flag()
            result = AST_declaration(self.items[1].value, flag)
            if isinstance(self.items[2], concrete_subscript):
                # skip array shape
                pos_in_statement = 3
            else:
                pos_in_statement = 2
        elif isinstance(self.items[0], token_datatype):
            primtype = AST_datatype_primitive(self.items[0].value)
            if primtype.name == 'char' and isinstance(self.items[1], concrete_subscript):
                # ignore char length for now
                #   not correct in C, but all declared chars in FPLO input
                #   are char arrays
                declaration_name = self.items[2].value
                pos_in_statement = 3
            else:
                declaration_name = self.items[1].value
                pos_in_statement = 2
            result = AST_declaration(declaration_name, primtype)
        if (
                (len(self.items) > pos_in_statement) and
                isinstance(self.items[pos_in_statement], concrete_subscript)
            ):
            # subscript in LHS declares shape
            if not isinstance(result, AST_declaration):
                raise RuntimeError('encountered subscript on non-declaration')
            result.set_shape(self.items[pos_in_statement].to_AST_shape())
            pos_in_statement = pos_in_statement + 1
        if len(self.items) <= pos_in_statement:
            # we are done, nothing more in statement
            return result
        if not (isinstance(self.items[pos_in_statement], token_operator) and
                self.items[pos_in_statement].value == '='):
            raise RuntimeError('unexpected item following declaration: %s' % (
                repr(self.items[pos_in_statement])))
        # we have an assignment
        new_assignment = AST_assignment()
        new_assignment.append(result)
        pos_in_statement = pos_in_statement + 1
        if len(self.items) <= pos_in_statement:
            raise RuntimeError('missing values in assignment')
        if len(self.items) > pos_in_statement + 1:
            raise RuntimeError('too many values in assignment')
        concrete_values = self.items[pos_in_statement]
        if isinstance(concrete_values, token_literal):
            new_value = AST_value_primitive()
            new_value.append(concrete_values.value)
            new_assignment.append(new_value)
            return new_assignment
        if isinstance(concrete_values, concrete_block):
            new_value = AST_value_list()
            if isinstance(result.child[1], AST_datatype_flag):
                # special case for 'flag' datatype, need to evaluate RHS for names
                (flag_names, flag_values) = concrete_values.flag_names_values()
                for flag_name in flag_names:
                    result.child[1].append(AST_declaration(flag_name, AST_datatype_primitive('logical')))
                for flag_value in flag_values:
                    new_value.append(flag_value)
            else:
                new_value.child = concrete_values.python_value()
            new_assignment.append(new_value)
        return new_assignment

    def python_value(self):
        def eval_accumulated(items):
            if len(items) == 1:
                return items[0]
            elif len(items) == 3 and items[1] == '/':
                return items[0] / items[2]
            else:
                LOGGER.error('concrete_statement.python_value:accum: %s', str(items))
                sys.stderr.write(self.indented_dump(''))

        result = []
        accum = []
        for item in self.items:
            if isinstance(item, token_literal):
                accum.append(item.value)
            elif isinstance(item, token_operator) and item.value == ',':
                if len(accum) > 0:
                    result.append(eval_accumulated(accum))
                accum = []
            elif isinstance(item, token_operator) and item.value == '/':
                # FPLO input contains fraction constants
                accum.append('/')
            elif isinstance(item, concrete_block):
                result.append(item.python_value())
            else:
                LOGGER.error('concrete_statement.python_value:item: %s', repr(item))
        if len(accum) > 0:
            result.append(eval_accumulated(accum))
        # sys.stderr.write('IN concrete_statement.python_value\n')
        # sys.stderr.write(self.indented_dump(''))
        # raise Exception('stop here')
        return result

    def flag_names_values(self):
        result_names = []
        result_values = []
        accum = []
        for item in self.items:
            if isinstance(item, (token_identifier, token_flag_value)):
                accum.append(item.value)
            elif isinstance(item, token_operator) and item.value == ',':
                if len(accum)!=2:
                    raise RuntimeError('flag_names_values encountered non-pair: ', str(accum))
                result_names.append(accum[0])
                result_values.append(accum[1])
                accum=[]
            else:
                raise RuntimeError('flag_names_values encountered unhandled item: ' + repr(item))
        if len(accum) > 0:
            if len(accum)!=2:
                raise RuntimeError('flag_names_values encountered non-pair: ', str(accum))
            result_names.append(accum[0])
            result_values.append(accum[1])
        return (result_names, result_values)

class concrete_block(concrete_node):
    def nomadmetainfo(self, prefix, indent):
        if len(self.items) < 1:
            return None
        for item in self.items:
            item.nomadmetainfo(prefix, indent)

    def to_AST(self):
        if len(self.items) < 1:
            return None
        result = AST_block()
        for item in self.items:
            item_AST = item.to_AST()
            if item_AST is not None:
                result.append(item_AST)
        if len(result) is not None:
            return result
        return None

    def python_value(self):
        if len(self.items) != 1:
            raise RuntimeError('python_value for block containing !=1 statement')
        return self.items[0].python_value()

    def flag_names_values(self):
        if len(self.items) != 1:
            raise RuntimeError('flag_names for block containing !=1 statement')
        return self.items[0].flag_names_values()


class concrete_subscript(concrete_statement):
    def __str__(self):
        result = (
            '[' +
            ', '.join(map(lambda i: "'" + str(i) + "'", self.items)) +
            ']'
        )
        return result

    def __repr__(self):
        result = (
            '[' +
            ', '.join(map(lambda i: "'" + repr(i) + "'", self.items)) +
            ']'
        )
        return "%10s %s" % (self.__class__.__name__, result)

    def to_AST_shape(self):
        result = AST_shape()
        for item in self.items:
            if isinstance(item, token_literal) and isinstance(item.value, int):
                result.append(item.value)
            elif isinstance(item, token_operator) and item.value == '*':
                # denote variable-length dimension by -1
                result.append(int(-1))
            elif isinstance(item, token_identifier):
                # TODO: check if length from identifier needs to be respected
                # for now treat as variable-length
                result.append(int(-1))
            else:
                raise Exception("unknown purpose of item in shape: %s" % (repr(item)))
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
        self.concrete_statements = concrete_block(None)
        self.concrete_statements.append(concrete_statement(self.concrete_statements))
        self.current_concrete_statement = self.concrete_statements.items[-1]

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
        if this_token is None:
            LOGGER.error("cannot match any token type to '%s'" % (
                line[pos_in_line:]))
            return None
        self._annotate(this_token.highlighted())
        # LOGGER.error('cls: %s', this_token.__class__.__name__)
        if isinstance(this_token, token_block_begin):
            newblock = concrete_block(self.current_concrete_statement)
            newblock.append(concrete_statement(newblock))
            self.current_concrete_statement.append(newblock)
            self.current_concrete_statement = newblock.items[0]
        elif isinstance(this_token, token_block_end):
            self.current_concrete_statement = self.current_concrete_statement.parent.parent
        elif isinstance(this_token, token_subscript_begin):
            newsubscript = concrete_subscript(self.current_concrete_statement)
            self.current_concrete_statement.append(newsubscript)
            self.current_concrete_statement = newsubscript
        elif isinstance(this_token, token_subscript_end):
            self.current_concrete_statement = self.current_concrete_statement.parent
        elif isinstance(this_token, token_statement_end):
            self.current_concrete_statement.parent.append(concrete_statement(self.current_concrete_statement.parent))
            self.current_concrete_statement = self.current_concrete_statement.parent.items[-1]
        elif isinstance(this_token, token_bad_input):
            self.bad_input = True
        elif isinstance(this_token, (token_line_comment, token_trailing_whitespace)):
            # skip comments and trailing whitespace
            pass
        elif isinstance(this_token, (
                    token_literal, token_flag_value, token_operator,
                    token_datatype, token_keyword, token_identifier
                )):
            self.current_concrete_statement.append(this_token)
        else:
            raise Exception("Unhandled token type " + this_token.__class__.__name__)
        return this_token.match.end()

    def onBad_input(self):
        """hook: called at the end of parsing if there was any bad input"""
        pass

    def onEnd_of_file(self):
        """hook: called at the end of parsing"""
        sys.stdout.flush()
        sys.stderr.flush()
        # sys.stderr.write(self.concrete_statements.indented_dump('')) # json.dumps(self.concrete_statements, sort_keys=True, indent=4, separators=(',', ': ')))
        # self.concrete_statements.nomadmetainfo('x_fplo_in','')
        AST = self.concrete_statements.to_AST()
        sys.stderr.write('AST:\n')
        sys.stderr.flush()
        sys.stderr.write(AST.indented_str(''))

if __name__ == "__main__":
    parser = FploInputParser(sys.argv[1], annotateFile=sys.stdout)
    parser.parse()
