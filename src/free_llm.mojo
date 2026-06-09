from std.python import Python
from std.sys import argv


def main() raises:
    Python.add_to_path("src")
    var cli = Python.import_module("free_llm_cli")
    var py_args = Python.list()
    var args = argv()
    for i in range(1, len(args)):
        py_args.append(String(args[i]))
    cli.run(py_args)
