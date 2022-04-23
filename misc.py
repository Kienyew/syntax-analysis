from .grammar import Grammar
from .LR import ParsingTable, SHIFT, REDUCE, ACCEPT


def generate_automaton_graphviz(pt: ParsingTable) -> str:
    '''
Generate the dot file representing automaton of a parsing table.
    '''
    lines = ['digraph {']
    lines += ['\tcompound = true']
    for i, items in pt.states.items():
        s = '\\n'.join(map(str, items.items)).replace('"', '\\"')
        cluster = '''\tsubgraph cluster_I{0} {{
\t    rankdir = TB
\t    label = <I<sub>{0}</sub>>
\t    node{0} [shape=none, label="{1}"]
\t}}'''.format(i, s)
        lines += [cluster]

    for (state, lookahead), (action, target) in pt.action.items():
        if action == SHIFT:
            lines += [f'\tnode{state} -> node{target} [label=" {lookahead}", lhead=cluster_I{target}, ltail=cluster_I{state}]']

    for (state, non_terminal), target in pt.goto.items():
        lines += [f'\tnode{state} -> node{target} [label=" {non_terminal}", lhead=cluster_I{target}, ltail=cluster_I{state}]']

    lines += ['}']

    return '\n'.join(lines)


def generate_canonical_set_latex(pt: ParsingTable) -> str:
    '''
Generate canonical set in pure latex representation.
    '''
    lines = []
    for i, items in sorted(pt.states.items()):
        lines += [rf'I_{i}  &= \left.\begin{{cases}}']
        items = sorted(items)
        for item in items:
            lines += [
                f'\t[{item.lhs} \\to {"~".join(map(str, item.rhs))}, {item.lookahead}] \\\\']
        lines += [r'\end{cases}\right\} \\']
    return '\n'.join(lines)


def generate_lr_parsing_table_repr(G: Grammar, pt: ParsingTable) -> str:
    lines = []
    for i, p in enumerate(G.productions):
        lines += [f'{i:2}. {p}']

    terminals = list(G.terminals())
    lines += ['']
    lines += ['\t'.join(map(str, ['STATE'] + terminals))]
    for state in pt.states:
        line = [f'{state: 3}']
        for t in G.terminals():
            action, target = pt.action.get((state, t), (None, None))
            if action == SHIFT:
                line += [f's{target}']
            elif action == REDUCE:
                line += [f'r{G.productions.index(target)}']
            elif action == ACCEPT:
                line += ['acc']
            else:
                line += ['']

        lines += ['\t'.join(line)]

    return '\n'.join(lines)
