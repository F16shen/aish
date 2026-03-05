from aish.tools.code_exec import BashTool
from aish.tools.fs_tools import EditFileTool, ReadFileTool, WriteFileTool
from aish.tools.final_answer import FinalAnswer


def get_tools_for_system_diagnose():
    return {
        "bash_exec": BashTool(),
        "read_file": ReadFileTool(),
        "write_file": WriteFileTool(),
        "edit_file": EditFileTool(),
        "final_answer": FinalAnswer(),
    }
