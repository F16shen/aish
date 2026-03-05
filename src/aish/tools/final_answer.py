"""
FinalAnswer tool for ending the SystemDiagnoseAgent loop and returning the answer.

This tool is used as a loop-exit signal when the SystemDiagnoseAgent has
completed its analysis and is ready to provide the final answer.
"""

from aish.tools.base import ToolBase


class FinalAnswer(ToolBase):
    """Tool that ends the SystemDiagnoseAgent loop and returns the answer."""

    name: str = "final_answer"
    description: str = "Ends the SystemDiagnoseAgent loop and returns the answer."
    parameters: dict = {
        "type": "object",
        "properties": {
            "answer": {
                "type": "string",
                "description": "The final diagnostic answer or solution to return.",
            }
        },
        "required": ["answer"],
    }

    def __call__(self, answer: str) -> str:
        """
        Return the supplied answer string.

        This tool simply returns the provided answer string, serving as
        the loop-exit signal for the SystemDiagnoseAgent.

        Args:
            answer: The final diagnostic answer or solution

        Returns:
            str: The supplied answer string
        """
        return answer
