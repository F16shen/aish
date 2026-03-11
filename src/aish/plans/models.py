"""Data models for Plan mode."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class PlanStatus(str, Enum):
    """Status of a plan."""

    DRAFT = "draft"  # Plan created, waiting for user approval
    APPROVED = "approved"  # Plan approved by user, ready to execute
    IN_PROGRESS = "in_progress"  # Plan is being executed
    PAUSED = "paused"  # Plan execution paused by user
    COMPLETED = "completed"  # All steps completed successfully
    FAILED = "failed"  # Plan execution failed
    CANCELLED = "cancelled"  # Plan cancelled by user


class StepStatus(str, Enum):
    """Status of a plan step."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    FAILED = "failed"


@dataclass
class PlanStep:
    """A single step in a plan."""

    number: int
    title: str
    description: str = ""
    commands: list[str] = field(default_factory=list)
    expected_outcome: str = ""
    verification: str = ""
    status: StepStatus = StepStatus.PENDING
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error_message: str = ""
    dependencies: list[int] = field(default_factory=list)  # Step numbers this depends on

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "number": self.number,
            "title": self.title,
            "description": self.description,
            "commands": self.commands,
            "expected_outcome": self.expected_outcome,
            "verification": self.verification,
            "status": self.status.value,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error_message": self.error_message,
            "dependencies": self.dependencies,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PlanStep":
        """Create from dictionary."""
        started_at = (
            datetime.fromisoformat(data["started_at"]) if data.get("started_at") else None
        )
        completed_at = (
            datetime.fromisoformat(data["completed_at"])
            if data.get("completed_at")
            else None
        )
        return cls(
            number=data["number"],
            title=data["title"],
            description=data.get("description", ""),
            commands=data.get("commands", []),
            expected_outcome=data.get("expected_outcome", ""),
            verification=data.get("verification", ""),
            status=StepStatus(data.get("status", "pending")),
            started_at=started_at,
            completed_at=completed_at,
            error_message=data.get("error_message", ""),
            dependencies=data.get("dependencies", []),
        )


class PlanStepModel(BaseModel):
    """Pydantic model for PlanStep validation."""

    number: int
    title: str
    description: str = ""
    commands: list[str] = Field(default_factory=list)
    expected_outcome: str = ""
    verification: str = ""
    status: StepStatus = StepStatus.PENDING
    dependencies: list[int] = Field(default_factory=list)


@dataclass
class Plan:
    """A plan for executing a complex task."""

    plan_id: str
    title: str
    description: str
    status: PlanStatus = PlanStatus.DRAFT
    steps: list[PlanStep] = field(default_factory=list)
    context: str = ""  # Additional context about the task
    author: str = ""  # User who created the plan
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    current_step: int = 1  # Next step to execute (1-indexed)
    file_path: str = ""  # Path to markdown file

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "plan_id": self.plan_id,
            "title": self.title,
            "description": self.description,
            "status": self.status.value,
            "steps": [step.to_dict() for step in self.steps],
            "context": self.context,
            "author": self.author,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "current_step": self.current_step,
            "file_path": self.file_path,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Plan":
        """Create from dictionary."""
        steps = [PlanStep.from_dict(s) for s in data.get("steps", [])]
        return cls(
            plan_id=data["plan_id"],
            title=data["title"],
            description=data["description"],
            status=PlanStatus(data.get("status", "draft")),
            steps=steps,
            context=data.get("context", ""),
            author=data.get("author", ""),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            current_step=data.get("current_step", 1),
            file_path=data.get("file_path", ""),
        )

    @classmethod
    def create(
        cls,
        title: str,
        description: str,
        context: str = "",
        author: str = "",
    ) -> "Plan":
        """Create a new plan with generated ID."""
        return cls(
            plan_id=str(uuid4())[:8],
            title=title,
            description=description,
            context=context,
            author=author or "user",
        )

    def get_step(self, step_number: int) -> PlanStep | None:
        """Get a step by number (1-indexed)."""
        for step in self.steps:
            if step.number == step_number:
                return step
        return None

    def get_next_pending_step(self) -> PlanStep | None:
        """Get the next pending step to execute."""
        for step in self.steps:
            if step.status == StepStatus.PENDING:
                return step
        return None

    def get_progress_summary(self) -> dict[str, int]:
        """Get progress summary."""
        return {
            "total": len(self.steps),
            "pending": sum(1 for s in self.steps if s.status == StepStatus.PENDING),
            "in_progress": sum(1 for s in self.steps if s.status == StepStatus.IN_PROGRESS),
            "completed": sum(1 for s in self.steps if s.status == StepStatus.COMPLETED),
            "skipped": sum(1 for s in self.steps if s.status == StepStatus.SKIPPED),
            "failed": sum(1 for s in self.steps if s.status == StepStatus.FAILED),
        }

    def to_markdown(self) -> str:
        """Convert plan to markdown format."""
        lines = [
            f"# {self.title}",
            "",
            f"**Status**: `{self.status.value}`",
            f"**Progress**: {sum(1 for s in self.steps if s.status == StepStatus.COMPLETED)}/{len(self.steps)} steps",
            f"**Created**: {self.created_at.strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "## Description",
            "",
            self.description,
            "",
            "## Steps",
            "",
        ]

        for step in self.steps:
            icon = {
                StepStatus.PENDING: "○",
                StepStatus.IN_PROGRESS: "◐",
                StepStatus.COMPLETED: "✓",
                StepStatus.SKIPPED: "⊘",
                StepStatus.FAILED: "✗",
            }.get(step.status, "?")

            lines.append(f"### {icon} Step {step.number}: {step.title}")
            lines.append(f"**Status**: `{step.status.value}`")

            if step.description:
                lines.append(f"**Description**: {step.description}")

            if step.commands:
                lines.append("**Commands**:")
                for cmd in step.commands:
                    lines.append(f"  - `{cmd}`")

            if step.expected_outcome:
                lines.append(f"**Expected**: {step.expected_outcome}")

            if step.verification:
                lines.append(f"**Verification**: {step.verification}")

            if step.error_message:
                lines.append(f"**Error**: {step.error_message}")

            lines.append("")

        if self.context:
            lines.extend(["## Context", "", self.context, ""])

        return "\n".join(lines)
