# Shim to wrap setup.py invocation with setuptools
SETUPTOOLS_SHIM = (
    "import ast, itertools, tokenize;__file__=%r;"
    "f=getattr(tokenize, 'open', open)(__file__);"
    "code=f.read().replace('\\r\\n', '\\n');"
    "f.close();"
    "mod = ast.parse(code, __file__);"
    "nodes = list(itertools.islice(("
    "node for node in mod.body "
    "if isinstance(node, ast.Assign) and "
    "len(node.targets) == 1 and "
    "isinstance(node.targets[0], ast.Name) and "
    "node.targets[0].id == '__requires__'"
    "), 0, 1));"
    "__requires__ = ast.literal_eval(nodes[0].value) if nodes else [];"
    "import setuptools;"
    "exec(compile(mod, __file__, 'exec'));"
)
