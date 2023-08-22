import json
from pprint import pprint
from collections import deque
from typing import Union
from pathlib import Path

from json_lexer import JsonLexer, JsonToken
import grammar
from grammar import Epsilon, Grammar, NonTerminal, Production, Terminal
import LL1


"""
JSON grammer:

value -> object
       | array
       | string
       | number
       | 'true'
       | 'false'
       | 'null'

object -> '{' '}'
        | '{' members '}'

members -> member 
         | member ',' members

member -> string : element

array -> '[' ']'
       | '[' elements ']'

elements -> element
          | element ',' elements

element = value
"""


Value = NonTerminal('Value')
Object = NonTerminal('Object')
Array = NonTerminal('Array')

Members = NonTerminal('Members')
Member = NonTerminal('Member')

Elements = NonTerminal('Elements')
Element = NonTerminal('Element')

string = Terminal('string')
number = Terminal('number')
true = Terminal('true')
false = Terminal('false')
null = Terminal('null')
lsb = Terminal('[')  # Left square bracket
rsb = Terminal(']')  # Right square bracket
lcb = Terminal('{')  # Left curly bracket
rcb = Terminal('}')  # Right curly bracket
comma = Terminal(',')
colon = Terminal(':')


def build_json_grammar() -> Grammar:
    json_grammar = Grammar(Value)

    json_grammar.add_production(Value, [Object])
    json_grammar.add_production(Value, [Array])
    json_grammar.add_production(Value, [string])
    json_grammar.add_production(Value, [number])
    json_grammar.add_production(Value, [true])
    json_grammar.add_production(Value, [false])
    json_grammar.add_production(Value, [null])

    json_grammar.add_production(Object, [lcb, rcb])
    json_grammar.add_production(Object, [lcb, Members, rcb])

    json_grammar.add_production(Members, [Member])
    json_grammar.add_production(Members, [Member, comma, Members])

    json_grammar.add_production(Member, [string, colon, Element])

    json_grammar.add_production(Array, [lsb, rsb])
    json_grammar.add_production(Array, [lsb, Elements, rsb])

    json_grammar.add_production(Elements, [Element])
    json_grammar.add_production(Elements, [Element, comma, Elements])

    json_grammar.add_production(Element, [Value])

    # The original grammar has common left factors,
    # we need to eliminate them in order to make it LL1 parsable.
    return grammar.left_factored(json_grammar)


class ParseTreeNode:
    def __init__(self, non_terminal: NonTerminal, children: list[Union[JsonToken, 'ParseTreeNode']], inh=None, syn=None):
        self.non_terminal = non_terminal
        self.children = children

    def as_graphviz(self, node2name) -> str:
        # BFS
        queue = deque([self])
        node2name = {self: 'n0'}
        name_index = 1
        lines = ['graph "" {']
        lines.append('node [shape=rectangle]')
        while len(queue) > 0:
            node = queue.popleft()
            lines.append(f'    {node2name[node]} [label="{node.non_terminal}"]')
            for child in node.children:
                if isinstance(child, JsonToken):
                    name = f't{name_index}'
                    name_index += 1
                    lines.append(f'    {name} [label="{child.value}"]')
                    lines.append(f'    {node2name[node]} -- {name}')
                else:
                    if child not in node2name:
                        node2name[child] = f'n{name_index}'
                        name_index += 1

                    lines.append(f'    {node2name[node]} -- {node2name[child]}')
                    queue.append(child)
            lines.append('')

        lines.append('}')
        return '\n'.join(lines)


def create_parse_tree(stream: str, grammar: Grammar, parsing_table: dict[tuple[NonTerminal, Terminal], set[Production]]):
    root = ParseTreeNode(grammar.start_symbol, [])
    tokens = list(JsonLexer(stream).tokens())
    token_i = 0

    def peek_token() -> JsonToken:
        return tokens[token_i]

    def next_token() -> JsonToken:
        nonlocal token_i

        token = tokens[token_i]
        token_i += 1
        return token

    def descent(parent: ParseTreeNode):
        token_terminal = Terminal(peek_token().type.value)
        production = next(iter(parsing_table[parent.non_terminal, token_terminal])).rhs
        for symbol in production:
            if isinstance(symbol, Terminal):
                token = next_token()
                parent.children.append(token)
            elif isinstance(symbol, Epsilon):
                continue
            elif isinstance(symbol, NonTerminal):
                node = ParseTreeNode(symbol, [])
                descent(node)
                parent.children.append(node)

    descent(root)
    return root


class SDTNode:
    def __init__(self, non_terminal: NonTerminal, inh, syn):
        self.non_terminal = non_terminal
        self.inh = inh
        self.syn = syn


def syntax_directed_translation(stream: str, json_grammar: Grammar) -> dict:
    """
    Parse an json text into a dictionary object,
    such that json.loads(stream) == syntax_directed_translation(stream, json_grammar)
    """

    Array, Array1, Element, Elements, Elements1, Member, Members, Members1, Object, Object1, Value = sorted(json_grammar.non_terminals())
    root = SDTNode(json_grammar.start_symbol, None, None)
    tokens = list(JsonLexer(stream).tokens())
    token_i = 0

    def peek_token() -> JsonToken:
        return tokens[token_i]

    def next_token() -> JsonToken:
        nonlocal token_i

        token = tokens[token_i]
        token_i += 1
        return token

    def descent(node: SDTNode):
        terminal = Terminal(peek_token().type.value)
        if node.non_terminal == Array:
            if terminal == lsb:
                next_token()    # consume [
                array1 = SDTNode(Array1, inh=[], syn=None)
                descent(array1)
                node.syn = array1.syn
            else:
                print(f'Unexpected token {terminal} at {node.non_terminal}')
        elif node.non_terminal == Array1:
            if terminal == lsb:
                elements = SDTNode(Elements, inh=node.inh, syn=None)
                descent(elements)
                next_token()    # consume ]
                node.syn = elements.syn
            elif terminal == rsb:
                next_token()    # consume ]
                node.syn = node.inh
            elif terminal in [false, null, number, string, true, lcb]:
                elements = SDTNode(Elements, inh=node.inh, syn=None)
                descent(elements)
                next_token()    # consume ]
                node.syn = elements.syn
            else:
                print(f'Unexpected token {terminal} at {node.non_terminal}')
        elif node.non_terminal == Element:
            if terminal in [lsb, false, null, number, string, true, lcb]:
                value = SDTNode(Value, inh=None, syn=None)
                descent(value)
                node.syn = value.syn
            else:
                print(f'Unexpected token {terminal} at {node.non_terminal}')
        elif node.non_terminal == Elements:
            if terminal in [lsb, false, null, number, string, true, lcb]:
                element = SDTNode(Element, inh=None, syn=None)
                descent(element)
                node.inh.append(element.syn)
                elements1 = SDTNode(Elements1, inh=node.inh, syn=None)
                descent(elements1)
                node.syn = elements1.syn
            else:
                print(f'Unexpected token {terminal} at {node.non_terminal}')
        elif node.non_terminal == Elements1:
            if terminal == comma:
                next_token()    # consume ,
                elements = SDTNode(Elements, inh=node.inh, syn=None)
                descent(elements)
                node.syn = elements.syn
            elif terminal == rsb:
                node.syn = node.inh
            else:
                print(f'Unexpected token {terminal} at {node.non_terminal}')
        elif node.non_terminal == Member:
            if terminal == string:
                key = next_token().value    # consume string
                next_token()    # consume :
                element = SDTNode(Element, inh=None, syn=None)
                descent(element)
                node.inh[key] = element.syn
            else:
                print(f'Unexpected token {terminal} at {node.non_terminal}')
        elif node.non_terminal == Members:
            if terminal == string:
                member = SDTNode(Member, inh=node.inh, syn=None)
                descent(member)
                members1 = SDTNode(Members1, inh=node.inh, syn=None)
                descent(members1)
                node.syn = members1.syn
            else:
                print(f'Unexpected token {terminal} at {node.non_terminal}')
        elif node.non_terminal == Members1:
            if terminal == comma:
                next_token()    # consume ,
                members = SDTNode(Members, inh=node.inh, syn=None)
                descent(members)
                node.syn = members.syn
            elif terminal == rcb:
                node.syn = node.inh
            else:
                print(f'Unexpected token {terminal} at {node.non_terminal}')
        elif node.non_terminal == Object:
            if terminal == lcb:
                next_token()    # consume {
                object1 = SDTNode(Object1, inh={}, syn=None)
                descent(object1)
                node.syn = object1.syn
            else:
                print(f'Unexpected token {terminal} at {node.non_terminal}')
        elif node.non_terminal == Object1:
            if terminal == string:
                members = SDTNode(Members, inh=node.inh, syn=None)
                descent(members)
                next_token()    # consume }
                node.syn = members.syn
            elif terminal == rcb:
                next_token()    # consume }
                node.syn = node.inh
            else:
                print(f'Unexpected token {terminal} at {node.non_terminal}')
        elif node.non_terminal == Value:
            if terminal == lsb:
                array = SDTNode(Array, inh=None, syn=None)
                descent(array)
                node.syn = array.syn
            elif terminal in [false, null, number, string, true]:
                node.syn = next_token().value     # consume value
            elif terminal == lcb:
                object = SDTNode(Object, inh=None, syn=None)
                descent(object)
                node.syn = object.syn
            else:
                print(f'Unexpected token {terminal} at {node.non_terminal}')

    descent(root)
    return root.syn


json_grammar = build_json_grammar()
# pprint(sorted(json_grammar.non_terminals()))

parsing_table = LL1.construct_parsing_table(json_grammar)
# pprint(parsing_table)

json_text = """ [1, 2, "hello", ["world"], { "pi": 3.14159, "numbers": [1, 2, 3, 4, 5] } ] """

ast = create_parse_tree(json_text, json_grammar, parsing_table)
# print(ast.as_graphviz({}))

pprint(syntax_directed_translation(json_text, json_grammar))
