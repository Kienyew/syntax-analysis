from grammar import Grammar, Production, Terminal, NonTerminal, Symbol, eof, first
from LR import ParsingTable, Item, ItemSet, CanonicalSet, dot, after_dot, SHIFT, REDUCE, ACCEPT
from copy import copy


def closure(G: Grammar, C: ItemSet) -> ItemSet:
    """
    compute LR(1) closure for C.
    """
    C = copy(C)
    workset = list(C)
    while len(workset) > 0:
        item = workset.pop()
        if not isinstance(B := after_dot(item), NonTerminal):
            continue

        # item = [A -> alpha • B beta, lookahead]
        beta = item.rhs[item.rhs.index(dot) + 2:]
        for p in G.productions_from(B):
            for b in first(beta + [item.lookahead], G):
                new_item = Item(B, [dot] + p.rhs, b)
                if new_item not in C:
                    C.add(new_item)
                    workset.append(new_item)

    return C


def goto(G: Grammar, C: ItemSet, x: Symbol):
    """
    compute LR(1) GOTO table for C.
    """
    GOTO = ItemSet()
    for item in C:
        pos = item.rhs.index(dot)
        if pos != len(item.rhs) - 1 and item.rhs[pos + 1] == x:
            rhs = item.rhs[:pos] + [x, dot] + item.rhs[pos + 2:]
            new_item = Item(item.lhs, rhs, item.lookahead)
            GOTO.add(new_item)

    return closure(G, GOTO)


def construct_canonical_set(G: Grammar) -> CanonicalSet:
    """
    Construct the LR(1) canonical set of the augmented grammar G,
    """

    # compute the CLOSURE({[S' -> •S, $]})
    start_item = Item(
        G.start_symbol, [dot] + G.productions_from(G.start_symbol)[0].rhs, eof)
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


# TODO: message error on conflicts
def construct_parsing_table(G: Grammar) -> ParsingTable:
    """
    Construct an canonical-LR(1) parsing table.
    (the code is almost same as the code to generate SLR(1) parsing table)

    The definition of class ParsingTable is as follow:
    ```
    class ParsingTable:
        states: dict[int, ItemSet]
        action: dict[tuple[int, Symbol]]
        goto: dict[tuple[int, Symbol]]
    ```
    where
        states: maps index of state to ItemSet.
        action: maps a tuple of (state, symbol) to an action, either SHIFT, REDUCE or ACCEPT.
            - if action is SHIFT, the return value is (SHIFT, state_to_shift).
            - if action is REDUCE, the return value is (REDUCE, production).
            - if action is ACCEPT, the return value is (ACCEPT, None).
        goto: the GOTO table, maps a tuple of (state, symbol) to a state.
    """

    C = construct_canonical_set(G)
    # impose an order to states, and ensure 0 is starting state
    i = 1
    states = {}
    for state in C:
        start = False
        for item in state:
            if item.lhs == G.start_symbol and item.rhs[0] == dot and item.lookahead == eof:
                start = True
                break

        if start:
            # this state is starting state
            states[0] = state
        else:
            # this state is not starting state
            states[i] = state
            i += 1

    r_states = {v: k for k, v in states.items()}

    # start filling in the parsing table
    ACTION = {}
    GOTO = {}

    for i, state in states.items():
        for item in state:
            A = after_dot(item)
            if isinstance(A, Terminal):
                # the symbol after • is a terminal
                ACTION[i, A] = (SHIFT, r_states[goto(G, state, A)])

            elif A is None and item.lhs == G.start_symbol and item.rhs[-1] == dot and item.lookahead == eof:
                # acceptable state: item = [S' -> S •, $]
                ACTION[i, eof] = (ACCEPT, None)

            elif A is None and item.lhs != G.start_symbol:
                # • is at the end of this item, as
                # B -> alpha •
                action = (REDUCE, Production(item.lhs, item.rhs[:-1]))
                ACTION[i, item.lookahead] = action

        # construct GOTO[i, n] for all non-terminals n
        for n in G.non_terminals():
            if len(s := goto(G, state, n)) > 0:
                GOTO[i, n] = r_states[s]

    return ParsingTable(states, ACTION, GOTO)
