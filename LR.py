# utilities & classes commonly used in all LR parsers.

from grammar import Grammar, Symbol, Terminal, NonTerminal
from dataclasses import dataclass, field
from copy import copy
from typing import Optional, Any, Union


# The • in an LR item
class Dot(Terminal):
    pass


dot = Dot('•')


# An LR item
@dataclass(eq=True, frozen=True)
class Item:
    lhs: NonTerminal
    rhs: list[Symbol]

    # lookahead different for LR(1) item, LALR(1) item, SLR(1) item
    lookahead: Union[Terminal, set[Terminal], None] = None

    def __repr__(self):
        r = ' '.join(map(str, self.rhs))
        if self.lookahead:
            return f'[{self.lhs} -> {r}, {self.lookahead}]'
        else:
            return f'[{self.lhs} -> {r}]'

    # let it hashable for more utilizable
    def __hash__(self):
        x = hash(self.lhs)
        if isinstance(self.lookahead, (Terminal, type(None))):
            x ^= hash(self.lookahead)
        elif isinstance(self.lookahead, set):
            for symbol in self.lookahead:
                x ^= hash(symbol)
        else:
            raise TypeError('invalid type for lookahead', type(self.lookahead))

        for y in self.rhs:
            x ^= hash(y)

        return x

    def __copy__(self):
        return Item(copy(self.lhs), self.rhs.copy(), copy(self.lookahead))

    def __eq__(self, x):
        return (self.lhs, self.rhs, self.lookahead) == (x.lhs, x.rhs, x.lookahead)

    def __lt__(self, other):
        return self.lhs < other.lhs


SHIFT = 'shift'
REDUCE = 'reduce'
ACCEPT = 'accept'


@dataclass(eq=True)
class ItemSet:
    """
    A hashable set of LR items
    """
    items: set[Item] = field(default_factory=set)

    def __hash__(self):
        x = 0
        for y in self.items:
            x ^ hash(y)
        return x

    def __iter__(self):
        return iter(self.items)

    def __copy__(self):
        return ItemSet(copy(self.items))

    def __contains__(self, item: Item):
        return item in self.items

    def __len__(self):
        return len(self.items)

    def add(self, item: Item):
        self.items.add(item)

    def remove(self, item: Item):
        self.items.remove(item)


@dataclass(frozen=True)
class CanonicalSet:
    s: set[ItemSet]

    def __hash__(self):
        x = 0
        for s in self.s:
            x ^ hash(s)
        return x

    def __contains__(self, items: ItemSet):
        return items in self.s

    def __iter__(self):
        return iter(self.s)

    def __len__(self):
        return len(self.s)

    def __copy__(self):
        return CanonicalSet(copy(self.s))

    def add(self, items: ItemSet):
        self.s.add(items)


@dataclass()
class ParsingTable:
    states: dict[int, ItemSet]
    action: dict[tuple[int, Symbol], Any]
    goto: dict[tuple[int, Symbol], Any]


def augmented_grammar(G: Grammar) -> Grammar:
    """
    return the augmented grammar.

    if the starting symbol of G is S, then this function returns a new grammar
    with new starting symbol S', and add a production S' -> S.
    """
    G = copy(G)
    new_start_symbol = G.start_symbol.new(G)
    G.add_production(new_start_symbol, [G.start_symbol])
    G.start_symbol = new_start_symbol
    return G


def after_dot(item: Item) -> Optional[Symbol]:
    """
    return the symbol after the • on rhs of the item, None if nothing after •.
    """
    pos = item.rhs.index(dot)
    if pos == len(item.rhs) - 1:
        return None
    else:
        return item.rhs[pos + 1]
