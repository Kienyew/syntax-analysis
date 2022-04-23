# define core utilities for syntax analysis

from dataclasses import dataclass, field
from typing import Union, Iterable


@dataclass(order=True, frozen=True)
class Terminal:
    symbol: str
    eof: bool = False

    def __repr__(self):
        return self.symbol


@dataclass(order=True, frozen=True)
class NonTerminal:
    symbol: str
    id: int = 0  # For auto naming when automatic generating new non-terminal

    def __repr__(self):
        if self.id == 0:
            return self.symbol
        else:
            # a suffix ' means generated non-terminal
            return f"{self.symbol}{self.id}'"

    def new(self, G: 'Grammar') -> 'NonTerminal':
        non_terminals = G.non_terminals()
        id = self.id
        while NonTerminal(self.symbol, id) in non_terminals:
            id += 1

        return NonTerminal(self.symbol, id)


@dataclass(frozen=True)
class Epsilon:
    def __repr__(self):
        return 'ε'

    # Place epsilon at last when doing sort
    def __lt__(self, o):
        return False

    def __gt__(self, o):
        return True


Symbol = Union[Terminal, NonTerminal]
eof = Terminal('$', eof=True)
epsilon = Epsilon()


@dataclass()
class Production:
    '''
    A class represents a production [lhs -> rhs]
    '''
    lhs: NonTerminal
    rhs: list[Symbol]

    def __repr__(self):
        r = ' '.join(map(str, self.rhs))
        return f'{self.lhs} -> {r}'

    # let it hashable for more utilizable
    def __hash__(self):
        x = hash(self.lhs)
        for y in self.rhs:
            x ^= hash(y)

        return x

    def __lt__(self, other):
        return self.lhs < other.lhs


@dataclass
class Grammar:
    '''
    A class represents the whole grammar. Grammar = (start_symbol, productions)
    '''
    start_symbol: NonTerminal = None
    productions: list[Production] = field(default_factory=list)

    def add_production(self, n: NonTerminal, s: list[Symbol]):
        p = Production(n, s)
        if p in self.productions:
            raise ValueError('production already exists')

        self.productions.append(Production(n, s))

    def non_terminals(self) -> set[NonTerminal]:
        """
        Return a set of all non-terminals in this grammar.
        """
        N = set()
        for p in self.productions:
            N.add(p.lhs)

        return N

    def terminals(self) -> set[Terminal]:
        """
        Return a set of all terminals in this grammar.
        """
        T = set()
        for p in self.productions:
            for symbol in p.rhs:
                if isinstance(symbol, Terminal):
                    T.add(symbol)

        return T

    def productions_from(self, lhs: NonTerminal) -> list[Production]:
        """
        return all productions in this grammar where left-hand-side is `lhs`.
        """
        P = []
        for p in self.productions:
            if p.lhs == lhs:
                P.append(p)

        return P

    def __copy__(self):
        return Grammar(self.start_symbol, self.productions.copy())


def terminals(*names) -> list[Terminal]:
    """
    return a list of terminals by the given names.
    """
    return [Terminal(name) for name in names]


def non_terminals(*names) -> list[NonTerminal]:
    """
    return a list of non-terminals by the given names.
    """
    return [NonTerminal(name) for name in names]


def first(s: Union[Iterable, Epsilon, Terminal, NonTerminal], G: Grammar) -> set[Union[Terminal, Epsilon]]:
    callstack = []  # to avoid infinite recursive call

    def _first(s):
        if s in callstack:
            return set()

        callstack.append(s)

        if isinstance(s, (Epsilon, Terminal)):
            S = {s}
        elif isinstance(s, NonTerminal):
            # s is non-terminal, all productions having the pattern
            # s -> a b c ... implies First(a b c ...) in First(s)
            S = set()
            for p in G.productions_from(s):
                S |= _first(p.rhs)
        elif isinstance(s, Iterable):
            # s is a sequence of symbols: s = [a b c ...]
            S = set()
            for q in s:
                firsts = _first(q)
                S |= firsts
                if epsilon not in firsts:
                    break

        else:
            return TypeError('bad arguments when calling function first:', s)

        callstack.pop()
        return S

    return _first(s)


def follow(s: NonTerminal, G: Grammar) -> set[Terminal]:
    """
    Compute the FOLLOW set of a non-terminal
    """

    # to avoid infinite recursive call
    callstack = []

    def _follow(s: NonTerminal):
        if s in callstack:
            return set()

        callstack.append(s)

        S = set()
        if s is G.start_symbol:
            S.add(eof)

        for p in G.productions:
            for i, e in enumerate(p.rhs):
                if e != s:
                    continue

                S |= first(p.rhs[i + 1:], G) - {epsilon}
                if i == len(p.rhs) - 1:
                    # A -> B s, add Follow(A) to Follow(S)
                    S |= _follow(p.lhs)
                elif epsilon in first(p.rhs[i + 1:], G):
                    # A -> B s C where epsilon in First(C), add Follow(A) to Follow(s)
                    S |= _follow(p.lhs)

        callstack.remove(s)
        return S

    return _follow(s)


def left_recursion_eliminated(G: Grammar):
    """
    Return a left recursion eliminated version of `G`
    """
    G = G.__copy__()
    A = [*G.non_terminals()]

    def expand_production(lhs: NonTerminal, target: NonTerminal):
        # Expand any occurence of `target` in the right hand side of any production from `lhs`,
        new_productions = []
        P = G.productions_from(target)
        for p in G.productions:
            if p.lhs == lhs and p.rhs[0] == target:
                for q in P:
                    new_productions.append(Production(lhs, q.rhs + p.rhs[1:]))
            else:
                new_productions.append(p)

        G.productions = new_productions

    # Converts all indirect left recursions to direct left recursions
    for i in range(len(A)):
        for j in range(i - 1):
            for p in G.productions_from(A[i]):
                if p.rhs[0] == A[j]:
                    expand_production(A[i], A[j])
                    break

    # Eliminate all direct left recursions
    new_productions = []
    new_nonterminals = set()
    for p in G.productions:
        if p.lhs == p.rhs[0]:
            new_lhs = p.lhs.new(G)
            for q in G.productions_from(p.lhs):
                if q.rhs[0] != p.lhs:
                    new_productions += [Production(p.lhs, q.rhs + [new_lhs])]

            new_productions += [Production(new_lhs, p.rhs[1:] + [new_lhs])]
            new_nonterminals.add(new_lhs)

        else:
            new_productions.append(p)

    for n in new_nonterminals:
        new_productions += [Production(n, [epsilon])]

    # eliminate repeated productions
    G.productions = list(set(new_productions))
    return G


def left_factored(G: Grammar) -> Grammar:
    """
    Return a left factored version of `G`
    """
    G = G.__copy__()

    def longest_common_prefix(a: list[Symbol], b: list[Symbol]) -> list[Symbol]:
        prefix = []
        for sa, sb in zip(a, b):
            if sa == sb:
                prefix += [sa]
            else:
                break

        return prefix

    def left_factor_one_symbol(n: NonTerminal) -> bool:
        # factor out all the productions of left-hand-side `n`
        # return value indicates something changed

        n_productions = G.productions_from(n)
        for i in range(len(n_productions)):
            # the production rhs to find common prefix
            key = n_productions[i].rhs

            # group of indices with the common prefix
            groups = [i]

            # the length of common prefix
            min_prefix = len(key)

            for j in range(i + 1, len(n_productions)):
                # do not includes in group if no common prefix with key
                if (prefix := longest_common_prefix(key, n_productions[j].rhs)):
                    min_prefix = min(len(prefix), min_prefix)
                    groups.append(j)

            # replace the productions with common prefix
            if len(groups) > 1:
                new_lhs = n.new(G)
                prefix = key[:min_prefix]
                G.productions += [Production(n, prefix + [new_lhs])]

                # add production rules: new_lhs -> suffixes
                for k in groups:
                    # if suffix is empty, allow the rule: new_lhs -> epsilon
                    suffix = n_productions[k].rhs[min_prefix:] or [epsilon]
                    G.productions.remove(n_productions[k])
                    G.productions += [Production(new_lhs, suffix)]

                # found one, good enough (fixed point algorithm)
                return True

        return False

    # fixed point algorithm, continue until nothing can progress
    while any(left_factor_one_symbol(n) for n in G.non_terminals()):
        continue

    return G
