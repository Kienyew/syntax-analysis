from grammar import Grammar, Production, Terminal, eof
import LR
import LR1
from LR import dot, SHIFT, REDUCE, ACCEPT
from collections import defaultdict


# TODO: message error on conflicts
def construct_parsing_table(G: Grammar) -> LR.ParsingTable:
    """
Construct a LALR(1) parsing table for grammar G.
This function will first construct the parsing table for LR(1),
and then combine the states with common core items into one state.

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
    pt = LR1.construct_parsing_table(G)

    # a map from state to its core state
    state_to_index: dict[LR.ItemSet, int] = {}
    index_to_core: dict[int, LR.ItemSet] = {}
    core_to_index: dict[LR.ItemSet, int] = {}

    # records what should be in the lookahead of one core item.
    # lookaheads =  mapping of (core state, core item) ->  lookaheads
    lookaheads: dict[tuple[int, LR.Item], set[Terminal]] = defaultdict(set)

    # merging all states having the same core
    # kinda mess
    index = 0
    for state in pt.states.values():
        core_state = LR.ItemSet()
        item_to_lookaheads = defaultdict(set)
        for item in state:
            core_item = LR.Item(item.lhs, item.rhs[:], set())
            item_to_lookaheads[core_item].add(item.lookahead)
            core_state.add(core_item)

        if core_state not in core_to_index:
            core_to_index[core_state] = index
            index_to_core[index] = core_state
            index += 1

        for core_item, symbols in item_to_lookaheads.items():
            for symbol in symbols:
                lookaheads[core_to_index[core_state], core_item].add(symbol)

        state_to_index[state] = core_to_index[core_state]

    # add the lookahead symbols to core states
    for (core_index, core_item), symbols in lookaheads.items():
        index_to_core[core_index].remove(core_item)
        index_to_core[core_index].add(
            LR.Item(core_item.lhs, core_item.rhs, symbols))

    # from now on the states with same core have been merged
    core_to_index = {v: k for k, v in index_to_core.items()}

    # start filling in the parsing table
    ACTION = {}
    GOTO = {}

    for state in pt.states.values():
        core_index = state_to_index[state]
        for item in index_to_core[core_index]:
            A = LR.after_dot(item)
            if isinstance(A, Terminal):
                # the symbol after • is a terminal
                goto_state = LR1.goto(G, state, A)
                goto_core_index = state_to_index[goto_state]
                ACTION[core_index, A] = (SHIFT, goto_core_index)

            elif A is None and item.lhs == G.start_symbol and item.rhs[-1] == dot and eof in item.lookahead:
                # acceptable state: item = [S' -> S •, $/../...]
                ACTION[core_index, eof] = (ACCEPT, None)

            elif A is None and item.lhs != G.start_symbol:
                # • is at the end of this item, as [B -> alpha •, ...}
                action = (REDUCE, Production(item.lhs, item.rhs[:-1]))
                for symbol in item.lookahead:
                    ACTION[core_index, symbol] = action

        # construct GOTO[i, n] for all non-terminals n
        for n in G.non_terminals():
            goto_state = LR1.goto(G, state, n)
            if len(goto_state) > 0:
                goto_core_index = state_to_index[goto_state]
                GOTO[core_index, n] = goto_core_index

    return LR.ParsingTable(index_to_core, ACTION, GOTO)
