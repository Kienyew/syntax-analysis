from LR0 import construct_canonical_set, goto
from LR import ParsingTable, dot, after_dot, SHIFT, REDUCE, ACCEPT
from grammar import Grammar, Terminal, Production, eof, follow


# TODO: message error on conflicting
def construct_parsing_table(G: Grammar) -> ParsingTable:
    """
    Construct an SLR(1) parsing table.

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
        for item in state:
            if item.lhs == G.start_symbol and item.rhs[0] == dot:
                # this item is starting state
                states[0] = state
                break
        else:
            # this item is not starting state
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

            elif A is None and item.lhs == G.start_symbol:
                # acceptable state: S' -> S •
                ACTION[i, eof] = (ACCEPT, None)

            elif A is None:
                # • is at the end of this item, as
                # B -> X Y ... •
                action = (REDUCE, Production(item.lhs, item.rhs[:-1]))
                for x in follow(item.lhs, G):
                    ACTION[i, x] = action

        # construct GOTO[i, n] for all non-terminals n
        for n in G.non_terminals():
            if len(s := goto(G, state, n)) > 0:
                GOTO[i, n] = r_states[s]

    return ParsingTable(states, ACTION, GOTO)
