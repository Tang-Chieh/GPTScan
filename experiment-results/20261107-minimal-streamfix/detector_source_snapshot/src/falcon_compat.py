"""Narrow Falcon 0.2.28 / Crytic Compile 0.3.3 type(C).{creation,runtime}Code shim.

Never edits site-packages, substitutes empty bytecode, or chooses by name alone.
"""
from importlib.metadata import version
from pathlib import Path


def contract_bytecode(compilation_unit, contract, runtime=False):
    expected = Path(contract.source_mapping.filename.absolute).resolve()
    matches = [unit for name, unit in compilation_unit.source_units.items()
               if Path(name.absolute).resolve() == expected and contract.name in unit.contracts_names]
    if len(matches) != 1:
        raise ValueError(f"Cannot uniquely resolve bytecode source for {contract.name}")
    unit = matches[0]
    return unit.bytecode_runtime(contract.name) if runtime else unit.bytecode_init(contract.name)


def is_bytecode_member(value):
    # Falcon can supply an unhashable Constant, so do not use a set here.
    return value in ("creationCode", "runtimeCode")


def install():
    import falcon.ir.convert as convert
    if getattr(convert._convert_type_contract, "_gptscan_source_unit_compat", False):
        return
    if (version("falcon-analyzer"), version("crytic-compile")) != ("0.2.28", "0.3.3"):
        raise RuntimeError("Bytecode compatibility shim requires tested Falcon 0.2.28 / Crytic Compile 0.3.3")
    original = convert._convert_type_contract

    def wrapped(ir, compilation_unit):
        if not is_bytecode_member(ir.variable_right):
            return original(ir, compilation_unit)
        contract = ir.variable_left.type.type
        bytecode = contract_bytecode(compilation_unit.crytic_compile_compilation_unit,
                                     contract, ir.variable_right == "runtimeCode")
        assignment = convert.Assignment(ir.lvalue, convert.Constant(str(bytecode)),
                                        convert.ElementaryType("bytes"))
        assignment.set_expression(ir.expression)
        assignment.set_node(ir.node)
        assignment.lvalue.set_type(convert.ElementaryType("bytes"))
        return assignment

    wrapped._gptscan_source_unit_compat = True
    convert._convert_type_contract = wrapped
    # A Yul declaration without an initializer has no `value` AST key in
    # newer solc exports. Preserve Falcon's existing absent-initializer branch.
    import importlib
    yul = importlib.import_module("falcon.solc_parsing.yul.parse_yul")
    original_yul = yul.parse_yul_variable_declaration
    def declaration(root, node, ast):
        return original_yul(root, node, {"value": None, **ast})
    yul.parse_yul_variable_declaration = declaration
    yul.parsers["YulVariableDeclaration"] = declaration
    original_literal = yul.parse_yul_literal
    def literal(root, node, ast):
        if 'value' not in ast and ast.get('kind') == 'string' and 'hexValue' in ast:
            # solc exports arbitrary Yul string bytes as hexValue; keep bytes
            # rather than assuming UTF-8 or substituting a missing value.
            from falcon.core.expressions.literal import Literal
            from falcon.core.solidity_types.elementary_type import ElementaryType
            return Literal(bytes.fromhex(ast['hexValue']).decode('latin1'), ElementaryType('string'))
        return original_literal(root, node, ast)
    yul.parsers['YulLiteral'] = literal
    original_yul_function = yul.YulScope.get_yul_local_function_from_name
    def yul_function(self, name):
        found = original_yul_function(self, name)
        parent = getattr(self, '_root', None)
        return found or (parent.get_yul_local_function_from_name(name) if parent is not None and parent is not self else None)
    yul.YulScope.get_yul_local_function_from_name = yul_function
    from falcon.solc_parsing.yul import evm_functions
    from falcon.core.declarations.solidity_variables import SOLIDITY_FUNCTIONS
    # Use the same opaque builtin-call representation as existing sload/mload.
    # This does NOT add inter-call transient-storage or memory alias analysis.
    for name, nargs, returns in (('tload', 1, 1), ('tstore', 2, 0), ('mcopy', 3, 0)):
        if name not in yul.builtins:
            yul.builtins.append(name)
        evm_functions.function_args[name] = [nargs, returns]
        SOLIDITY_FUNCTIONS[name + '(' + ','.join(['uint256'] * nargs) + ')'] = ['uint256'] * returns
    # Tuple expressions deliberately contain None for omitted tuple slots.
    # There is no expression to split in those slots; retain the None copies.
    from falcon.utils.expression_manipulations import SplitTernaryExpression
    original_copy = SplitTernaryExpression.copy_expression
    def copy_expression(self, expression, true_expression, false_expression):
        if expression is None:
            return
        from falcon.core.expressions.index_access import IndexAccess
        from falcon.utils.expression_manipulations import f_expressions
        if isinstance(expression, IndexAccess) and not self.condition:
            true_expression._expressions = []
            false_expression._expressions = []
            for child in expression.expressions:
                if self.apply_copy(child, true_expression, false_expression, f_expressions):
                    self.copy_expression(child, true_expression.expressions[-1], false_expression.expressions[-1])
            return
        return original_copy(self, expression, true_expression, false_expression)
    SplitTernaryExpression.copy_expression = copy_expression
    original_call = convert.convert_type_of_high_and_internal_level_call
    def resolve_call(ir, contract):
        try:
            return original_call(ir, contract)
        except AttributeError as error:
            raise RuntimeError(f"Falcon unresolved call: name={ir.function_name}, contract={contract.name}, argument_types={[str(getattr(a, 'type', None)) for a in ir.arguments]}; source={ir.node.source_mapping}; {error}") from error
    convert.convert_type_of_high_and_internal_level_call = resolve_call
    from falcon.core.cfg.node import Node
    original_read_write = Node._find_read_write_call
    def read_write(self):
        try:
            return original_read_write(self)
        except AssertionError as error:
            calls = [(str(ir), type(getattr(ir, 'function', None)).__name__) for ir in self.irs]
            raise RuntimeError(f"Falcon read/write assertion: {self.source_mapping}; {calls}") from error
    Node._find_read_write_call = read_write
    import inspect
    # Falcon compares an event NAME against a dictionary keyed by SIGNATURE.
    # Use the declared event names, keeping its original EventCall conversion.
    source = inspect.getsource(convert.extract_tmp_call)
    needle = 'str(ins.ori.variable_right) in ins.ori.variable_left.events_as_dict'
    if needle not in source:
        raise RuntimeError('Unexpected Falcon event conversion implementation')
    source = source.replace(needle, 'str(ins.ori.variable_right) in [e.name for e in ins.ori.variable_left.events]')
    source = source.replace('str(ins.ori.variable_right) in ins.ori.variable_left.custom_errors_as_dict',
                            'str(ins.ori.variable_right) in [e.name for e in ins.ori.variable_left.custom_errors]')
    source = source.replace('custom_error = ins.ori.variable_left.custom_errors_as_dict[\n                    str(ins.ori.variable_right)\n                ]',
                            'custom_error = next(e for e in ins.ori.variable_left.custom_errors if e.name == str(ins.ori.variable_right))')
    namespace = dict(vars(convert))
    exec(compile(source, '<gptscan-falcon-event-compat>', 'exec'), namespace)
    extract = namespace['extract_tmp_call']
    def extract_call(ins, contract):
        origin = getattr(ins, 'ori', None)
        left = getattr(origin, 'variable_left', None)
        if isinstance(left, convert.SolidityImportPlaceHolder):
            target = Path(ins.compilation_unit.crytic_compile.filename_lookup(str(left.import_directive.filename)).absolute).resolve()
            errors = [e for e in ins.compilation_unit.custom_errors
                      if Path(e.source_mapping.filename.absolute).resolve() == target
                      and e.name == str(origin.variable_right) and len(e.parameters) == ins.nbr_arguments]
            if len(errors) == 1:
                call = convert.SolidityCall(convert.SolidityCustomRevert(errors[0]), ins.nbr_arguments, ins.lvalue, ins.type_call)
                call.set_expression(ins.expression)
                call.call_id = ins.call_id
                return call
            if len(errors) > 1:
                raise ValueError('Ambiguous imported custom error')
            if not errors and str(origin.variable_right).isupper():
                available = [(e.name, e.source_mapping.filename.absolute) for e in ins.compilation_unit.custom_errors if e.name == str(origin.variable_right)]
                raise ValueError(f'Unresolved imported custom error: target={target}, available={available}')
        return extract(ins, contract)
    convert.extract_tmp_call = extract_call
    # A tuple IR variable may already hold the list of component types (rather
    # than a wrapper exposing `.type`). Preserve the exact indexed component.
    source = inspect.getsource(convert.propagate_types)
    needle = 'types = ir.tuple.type.type'
    if needle not in source:
        raise RuntimeError('Unexpected Falcon tuple conversion implementation')
    source = source.replace(needle, 'types = ir.tuple.type if isinstance(ir.tuple.type, list) else ir.tuple.type.type')
    namespace = dict(vars(convert))
    exec(compile(source, '<gptscan-falcon-tuple-compat>', 'exec'), namespace)
    convert.propagate_types = namespace['propagate_types']
    from falcon.solc_parsing.declarations.contract import ContractSolc
    original_using = ContractSolc.analyze_using_for
    def using_for(self):
        original_using(self)
        unit = self.compilation_unit
        from falcon.core.solidity_types.user_defined_type import UserDefinedType
        for filename, binding in getattr(unit.crytic_compile_compilation_unit, '_gptscan_global_using', []):
            scope = unit.get_scope(filename)
            name = binding['typeName']['typeDescriptions']['typeString']
            alias = scope.user_defined_types.get(name)
            if alias is None and name.startswith('struct '):
                structure_name = name[len('struct '):]
                structs = [s for s in scope.structures.values() if s.name == structure_name]
                if len(structs) == 1:
                    alias = UserDefinedType(structs[0])
            libraries = [c for c in unit.contracts if c.id == binding['libraryName']['referencedDeclaration']]
            if alias is None or len(libraries) != 1:
                raise ValueError(f'Cannot resolve compiler global using binding: {name}')
            library = UserDefinedType(libraries[0])
            entries = self.underlying_contract.using_for.setdefault(alias, [])
            if library not in entries:
                entries.append(library)
    ContractSolc.analyze_using_for = using_for
    # FileScope's name dictionary can lose one of two imported Math libraries.
    # A solc referencedDeclaration is unit-local and identifies the exact one.
    expressions = importlib.import_module('falcon.solc_parsing.expressions.expression_parsing')
    original_find = expressions.find_variable
    def find_variable(name, caller, referenced_declaration=None, *args, **kwargs):
        if referenced_declaration is not None:
            matches = [c for c in caller.compilation_unit.contracts if c.id == referenced_declaration]
            if len(matches) == 1:
                return matches[0], False
        return original_find(name, caller, referenced_declaration, *args, **kwargs)
    expressions.find_variable = find_variable


def expand_global_using(compiled):
    """Represent solc global library bindings in Falcon's contract-only model.

    Global bindings are recorded from AST identity. Explicit user-defined
    operators are lowered to their compiler-selected internal function calls.
    Only the in-memory view changes; archived/source bytes remain intact.
    """
    for unit in compiled.compilation_units.values():
        declarations = {}
        def collect(value):
            if isinstance(value, dict):
                if value.get('nodeType') == 'FunctionDefinition':
                    declarations[value['id']] = value
                for child in value.values():
                    collect(child)
            elif isinstance(value, list):
                for child in value:
                    collect(child)
        for source in unit.source_units.values():
            collect(source.ast)
        def lower(value):
            if isinstance(value, dict):
                for child in list(value.values()):
                    lower(child)
                if value.get('nodeType') in ('BinaryOperation', 'UnaryOperation') and value.get('function'):
                    function = declarations.get(value['function'])
                    if function is None:
                        raise ValueError('Missing compiler-selected user operator declaration')
                    arguments = ([value['leftExpression'], value['rightExpression']]
                                 if value['nodeType'] == 'BinaryOperation' else [value['subExpression']])
                    types = ','.join(p['typeDescriptions']['typeString'] for p in function['parameters']['parameters'])
                    returns = ','.join(p['typeDescriptions']['typeString'] for p in function['returnParameters']['parameters'])
                    identifier = {'nodeType': 'Identifier', 'id': -value['id'], 'src': value['src'],
                                  'name': function['name'], 'referencedDeclaration': function['id'],
                                  'overloadedDeclarations': [], 'typeDescriptions': {'typeString': f'function ({types}) pure returns ({returns})'}}
                    replacement = {'nodeType': 'FunctionCall', 'id': value['id'], 'src': value['src'],
                                   'kind': 'functionCall', 'names': [], 'tryCall': False,
                                   'expression': identifier, 'arguments': arguments, 'typeDescriptions': value['typeDescriptions']}
                    value.clear()
                    value.update(replacement)
            elif isinstance(value, list):
                for child in value:
                    lower(child)
        for source in unit.source_units.values():
            lower(source.ast)
        unit._gptscan_global_using = [(filename.absolute, node) for filename, s in unit.source_units.items()
                    for node in s.ast.get('nodes', [])
                    if node.get('nodeType') == 'UsingForDirective' and node.get('global')
                    and node.get('libraryName') and node.get('typeName')]
