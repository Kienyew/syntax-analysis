from collections.abc import Iterator
from dataclasses import dataclass
from enum import Enum
from typing import Union
from string import whitespace, hexdigits, digits


class JsonType(Enum):
    TRUE = 'true'
    FALSE = 'false'
    NULL = 'null'
    LEFT_SQUARE_BRACKET = '['
    RIGHT_SQUARE_BRACKET = ']'
    LEFT_CURLY_BRACKET = '{'
    RIGHT_CURLY_BRACKET = '}'
    NUMBER = 'number'
    STRING = 'string'
    COMMA = ','
    COLON = ':'


@dataclass
class JsonToken:
    type: JsonType
    value: Union[bool, float, str, None]


class JsonLexer:
    def __init__(self, stream: str):
        # The json element string
        self.stream = stream

        # The pointer of character in stream
        self.head = 0

    def advance(self, n):
        """
        Advance head by n
        """
        self.head += n

    def peek(self) -> str:
        """
        Return the current character pointed by self.head
        """
        if self.head >= len(self.stream):
            raise RuntimeError('Peek at end of file')

        return self.stream[self.head]

    def skip_ws(self):
        """
        Advance self.head until next non-whitespace character, or eof
        """
        while self.head < len(self.stream) and self.peek() in whitespace:
            self.advance(1)

    def expect_literal(self, literal: str):
        """
        Expect the literal at self.head is literal, then skip through the literal
        """
        if self.head + len(literal) > len(self.stream):
            raise RuntimeError(f'Cannot parse "{literal}"')

        if self.stream[self.head:self.head + len(literal)] != literal:
            raise RuntimeError(f'Cannot parse "{literal}"')

        self.advance(len(literal))

    def next_char(self) -> str:
        c = self.peek()
        self.advance(1)
        return c

    def next_string(self) -> str:
        """
        Advance self.head through next json string, and return the content of the json string
        """
        self.expect_literal('"')
        characters = []
        while self.head < len(self.stream) and self.peek() != '"':
            # Found escape
            if self.peek() == '\\':
                # skip \
                self.advance(1)
                c = self.next_char()
                match c:
                    case '"' | '\\' | '/':
                        characters.append(c)
                    case 'b':
                        characters.append('\b')
                    case 'f':
                        characters.append('\f')
                    case 'n':
                        characters.append('\n')
                    case 'r':
                        characters.append('\r')
                    case 't':
                        characters.append('\t')
                    case 'u':
                        h1 = self.next_char()
                        h2 = self.next_char()
                        h3 = self.next_char()
                        h4 = self.next_char()
                        if any(h not in hexdigits for h in (h1, h2, h3, h4)):
                            raise RuntimeError(f'Invalid hex digits \\u{h1}{h2}{h3}{h4}')

                        characters.append(chr(int(f'{h1}{h2}{h3}{h4}', 16)))
            else:
                characters.append(self.next_char())

        self.expect_literal('"')
        return ''.join(characters)

    def next_number(self) -> float:
        # We'll use python float() function to convert string to float for simplicity
        number_str = ""

        if self.peek() == '-':
            number_str += self.next_char()

        while self.head < len(self.stream) and self.peek() in digits:
            number_str += self.next_char()

        if self.head < len(self.stream) and self.peek() == '.':
            number_str += '.'
            self.advance(1)

        while self.head < len(self.stream) and self.peek() in digits:
            number_str += self.next_char()

        if self.head < len(self.stream) and (self.peek() == 'E' or self.peek() == 'e'):
            number_str += self.next_char()

        if self.head < len(self.stream) and (self.peek() == '-' or self.peek() == '+'):
            number_str += self.next_char()

        while self.head < len(self.stream) and self.peek() in digits:
            number_str += self.next_char()

        return float(number_str)

    def tokens(self) -> Iterator[JsonToken]:
        """
        Perform the lexing, yields the iterators of token
        """

        self.skip_ws()
        while self.head < len(self.stream):
            match self.peek():
                case 't':
                    self.expect_literal('true')
                    yield JsonToken(JsonType.TRUE, True)
                case 'f':
                    self.expect_literal('false')
                    yield JsonToken(JsonType.TRUE, False)
                case 'n':
                    self.expect_literal('null')
                    yield JsonToken(JsonType.NULL, None)
                case '0' | '1' | '2' | '3' | '4' | '5' | '6' | '7' | '8' | '9' | '-':
                    value = self.next_number()
                    yield JsonToken(JsonType.NUMBER, value)
                case '"':
                    value = self.next_string()
                    yield JsonToken(JsonType.STRING, value)
                case '{':
                    self.advance(1)
                    yield JsonToken(JsonType.LEFT_CURLY_BRACKET, '{')
                case '}':
                    self.advance(1)
                    yield JsonToken(JsonType.RIGHT_CURLY_BRACKET, '}')
                case '[':
                    self.advance(1)
                    yield JsonToken(JsonType.LEFT_SQUARE_BRACKET, '[')
                case ']':
                    self.advance(1)
                    yield JsonToken(JsonType.RIGHT_SQUARE_BRACKET, ']')
                case ',':
                    self.advance(1)
                    yield JsonToken(JsonType.COMMA, ',')
                case ':':
                    self.advance(1)
                    yield JsonToken(JsonType.COLON, ':')
                case c:
                    raise RuntimeError(f'Unexpected character "{c}"')

            self.skip_ws()


#  json_str = """
#  {
#      "a": [1, 2, 3],
#      "b": false,
#      "c": -0.0314e2,
#      "d": "\\u1234"
#  }
#  """
#
#  for token in JsonLexer(json_str).tokens():
#      print(f'Token({token.value})')
