from pydantic import BaseModel


class Command(BaseModel):
    command: str
    args: list[str]


class Error(Command):
    error: str


class BuiltinCommand(Command):
    pass


class CommandDispatcher:
    @staticmethod
    def parse(input: str) -> Command:
        return Error(command="", args=[], error="invalid")

    @staticmethod
    def builtin_commands() -> list[str]:
        return []

    @staticmethod
    def is_builtin_command(cmd: str) -> bool:
        return cmd in CommandDispatcher.builtin_commands()
