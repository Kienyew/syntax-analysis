from syntax_analysis import LL1
from syntax_analysis import first, follow
from syntax_analysis import NonTerminal
from syntax_analysis import Grammar, terminals, non_terminals
from pprint import pprint

# Define the grammar:
#   Expr -> Expr + Term
#   	  | Expr - Term
#   	  | Term
#
#   Term -> Term * Factor
#   	  | Expr / Term
#   	  | Factor
#
#   Factor -> num | ( Expr )


def expr_grammar():
    Expr, Term, Factor = non_terminals('Expr', 'Term', 'Factor')
    plus, minus, times, div, num, lp, rp = terminals(
        '+', '-', '*', '/', 'num', '(', ')')

    G = Grammar(Expr)  # Expr is starting symbol
    G.add_production(Expr, [Expr, plus, Term])
    G.add_production(Expr, [Expr, minus, Term])
    G.add_production(Expr, [Term])
    G.add_production(Term, [Term, times, Factor])
    G.add_production(Term, [Expr, div, Term])
    G.add_production(Term, [Factor])
    G.add_production(Factor, [num])
    G.add_production(Factor, [lp, Expr, rp])
    # pprint(G)

    return G


def parentheses_grammar():
    Start, List, Pair = non_terminals('S', 'List', 'Pair')
    lp, rp = terminals('(', ')')
    G = Grammar(Start)
    G.add_production(Start, [List])
    G.add_production(List, [List, Pair])
    G.add_production(List, [Pair])
    G.add_production(Pair, [lp, Pair, rp])
    G.add_production(Pair, [lp, rp])

    return G

# First and Follow


def first_and_follow():
    G = expr_grammar()
    print(first(Expr, G))   # {(, num}
    print(follow(Expr, G))  # {), /, $, -, +}


# Create LL(1) Parsing Table
def create_ll1_parsing_table():
    S = NonTerminal('S')
    plus, times, a = terminals('+', '*', 'a')
    G = Grammar(S)
    G.add_production(S, [plus, S, S])
    G.add_production(S, [times, S, S])
    G.add_production(S, [a])
    pprint(LL1.construct_parsing_table(G))
    # {(S, *): {S -> * S S},
    #  (S, +): {S -> + S S},
    #  (S, a): {S -> a}}


# Create LR(1) Parsing Table
def create_lr1_parsing_table():
    from syntax_analysis import LR1
    from syntax_analysis.misc import generate_automaton_graphviz

    G = parentheses_grammar()
    canonical_set = LR1.construct_canonical_set(G)
    pt = LR1.construct_parsing_table(G)
    # pprint(canonical_set)  # CanonicalSet(...)
    # pprint(pt)  # ParsingTable(...)
    print(generate_automaton_graphviz(pt))



# Create LALR(1) Parsing Table
def create_lalr1_parsing_table():
    from syntax_analysis import LALR1
    from syntax_analysis.misc import generate_automaton_graphviz
    G = parentheses_grammar()
    pt = LALR1.construct_parsing_table(G)
    print(generate_automaton_graphviz(pt))

create_lalr1_parsing_table()
