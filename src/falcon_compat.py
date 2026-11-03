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


def install():
    import falcon.ir.convert as convert
    if getattr(convert._convert_type_contract, "_gptscan_source_unit_compat", False):
        return
    if (version("falcon-analyzer"), version("crytic-compile")) != ("0.2.28", "0.3.3"):
        raise RuntimeError("Bytecode compatibility shim requires tested Falcon 0.2.28 / Crytic Compile 0.3.3")
    original = convert._convert_type_contract

    def wrapped(ir, compilation_unit):
        if ir.variable_right not in {"creationCode", "runtimeCode"}:
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
