# All utility functions needed by top down parsing (mainly LL(1) parsing)
from collections import defaultdict
from .grammar import Production, Grammar, epsilon, first, follow


def construct_parsing_table(G: Grammar) -> dict[dict[Production]]:
    """
    Create the parsing table for LL(1) parsing, that says if the grammar is left recursion,
    or have common left factors, this function might not work as expected.

    Returned table M is a dictionary where M[NonTerminal, Terminal] are the productions to choose.
    The entry is a set of productions can be chosen. If the length of the set of productions
    is longer than one, then the grammar is not LL(1) parsable, theoretically (or valid but
    degenerated, you need to check yourself)
    """
    M = defaultdict(set)
    for p in G.productions:
        for terminal in first(p.rhs, G) - {epsilon}:
            M[p.lhs, terminal].add(p)

        if epsilon in first(p.rhs, G):
            for terminal in follow(p.lhs, G):
                M[p.lhs, terminal].add(p)

    return dict(M)
