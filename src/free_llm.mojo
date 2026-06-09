from std.python import Python


def main() raises:
    Python.add_to_path("src")
    var cli = Python.import_module("free_llm_cli")
    cli.main()
