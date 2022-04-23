# utilities used in LR(0) parser.
from grammar import Grammar, Symbol, NonTerminal
from copy import copy
from LR import CanonicalSet, Item, ItemSet, dot, after_dot


def closure(G: Grammar, C: ItemSet) -> ItemSet:
    """
    construct LR(0) closure for C.
    """
    C = copy(C)
    workset = list(C)
    while len(workset) > 0:
        item = workset.pop()
        if isinstance(B := after_dot(item), NonTerminal):
            for prod in G.productions_from(B):
                new_item = Item(prod.lhs, [dot] + prod.rhs)
                if new_item not in C.items:
                    C.add(new_item)
                    workset.append(new_item)

    return C


def goto(G: Grammar, C: ItemSet, x: Symbol) -> ItemSet:
    """
    Compute GOTO(I, x)
    """
    GOTO = ItemSet()

    # move the • right by one for all available transitions
    for item in closure(G, C):
        pos = item.rhs.index(dot)
        if pos != len(item.rhs) - 1 and item.rhs[pos + 1] == x:
            rhs = item.rhs[:pos] + [x, dot] + item.rhs[pos + 2:]
            new_item = Item(item.lhs, rhs)
            GOTO.add(new_item)

    # then compute the closure of the translated items
    return closure(G, GOTO)


def construct_canonical_set(G: Grammar) -> CanonicalSet:
    """
    Construct the LR(0) canonical set of the augmented grammar G,
    the canonical set is a set of set, where each set
    are LR items representing an LR parsing state.
    """

    # compute the CLOSURE({S' -> •S})
    start_item = Item(G.start_symbol, [dot] +
                      G.productions_from(G.start_symbol)[0].rhs)
    start = ItemSet({start_item})
    C = CanonicalSet({closure(G, start)})

    symbols = G.non_terminals() | G.terminals()
    workset = list(C)
    while len(workset) > 0:
        items = workset.pop()
        for symbol in symbols:
            GOTO = goto(G, items, symbol)
            if len(GOTO) != 0 and GOTO not in C:
                C.add(GOTO)
                workset.append(GOTO)
    return C
