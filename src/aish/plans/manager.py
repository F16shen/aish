"""PlanManager for managing plans in the Plan mode."""

from pathlib import Path
from typing import Any

from aish.plans.models import Plan, PlanStatus, PlanStep, StepStatus
from aish.plans.storage import PlanStorage


class PlanManager:
    """Manager for creating, loading, and updating plans."""

    def __init__(self, data_dir: Path | None = None):
        """Initialize the plan manager.

        Args:
            data_dir: Base directory for storing plans
        """
        self.storage = PlanStorage(data_dir)

    def create_plan(
        self,
        title: str,
        description: str,
        steps: list[dict],
        context: str = "",
        author: str = "",
    ) -> Plan:
        """Create a new plan.

        Args:
            title: Plan title
            description: Plan description
            steps: List of step dictionaries with keys: title, description, commands, etc.
            context: Additional context about the task
            author: User who created the plan

        Returns:
            The created plan
        """
        plan = Plan.create(
            title=title,
            description=description,
            context=context,
            author=author,
        )

        # Add steps
        for i, step_data in enumerate(steps, 1):
            step = PlanStep(
                number=i,
                title=step_data.get("title", f"Step {i}"),
                description=step_data.get("description", ""),
                commands=step_data.get("commands", []),
                expected_outcome=step_data.get("expected_outcome", ""),
                verification=step_data.get("verification", ""),
                status=StepStatus.PENDING,
                dependencies=step_data.get("dependencies", []),
            )
            plan.steps.append(step)

        self.storage.save_plan(plan)
        return plan

    def save_plan(self, plan: Plan) -> None:
        """Save an existing plan.

        Args:
            plan: The plan to save
        """
        self.storage.save_plan(plan)

    def load_plan(self, plan_id: str) -> Plan | None:
        """Load a plan by ID.

        Args:
            plan_id: The plan ID to load

        Returns:
            The loaded plan or None if not found
        """
        return self.storage.load_plan(plan_id)

    def list_plans(
        self,
        status: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """List plans with optional filtering.

        Args:
            status: Filter by plan status (draft, approved, in_progress, etc.)
            limit: Maximum number of plans to return

        Returns:
            List of plan summary dictionaries
        """
        return self.storage.list_plans(status=status, limit=limit)

    def update_plan_status(self, plan_id: str, status: PlanStatus) -> Plan | None:
        """Update the status of a plan.

        Args:
            plan_id: The plan ID
            status: New status

        Returns:
            The updated plan or None if not found
        """
        plan = self.storage.load_plan(plan_id)
        if plan is None:
            return None

        plan.status = status
        self.storage.save_plan(plan)
        return plan

    def update_step_status(
        self,
        plan_id: str,
        step_number: int,
        status: StepStatus,
        error_message: str = "",
    ) -> Plan | None:
        """Update the status of a step.

        Args:
            plan_id: The plan ID
            step_number: The step number (1-indexed)
            status: New status
            error_message: Error message if status is FAILED

        Returns:
            The updated plan or None if not found
        """
        plan = self.storage.load_plan(plan_id)
        if plan is None:
            return None

        step = plan.get_step(step_number)
        if step is None:
            return None

        step.status = status
        step.error_message = error_message

        # Update timestamps
        if status == StepStatus.IN_PROGRESS and step.started_at is None:
            from datetime import datetime

            step.started_at = datetime.now()
        elif status in (StepStatus.COMPLETED, StepStatus.SKIPPED, StepStatus.FAILED):
            from datetime import datetime

            if step.completed_at is None:
                step.completed_at = datetime.now()

        # Update plan current_step if completing this step
        if status == StepStatus.COMPLETED:
            # Find next pending step
            for s in plan.steps:
                if s.status == StepStatus.PENDING:
                    plan.current_step = s.number
                    break
            else:
                # All steps done
                plan.current_step = len(plan.steps) + 1

        self.storage.save_plan(plan)
        return plan

    def delete_plan(self, plan_id: str) -> bool:
        """Delete a plan.

        Args:
            plan_id: The plan ID to delete

        Returns:
            True if deleted, False if not found
        """
        return self.storage.delete_plan(plan_id)

    def get_markdown_path(self, plan_id: str) -> Path:
        """Get the markdown file path for a plan.

        Args:
            plan_id: The plan ID

        Returns:
            Path to the markdown file
        """
        return self.storage.get_markdown_path(plan_id)

    def can_resume_plan(self, plan_id: str) -> bool:
        """Check if a plan can be resumed.

        Args:
            plan_id: The plan ID

        Returns:
            True if the plan can be resumed
        """
        plan = self.storage.load_plan(plan_id)
        if plan is None:
            return False

        return plan.status in (PlanStatus.APPROVED, PlanStatus.IN_PROGRESS, PlanStatus.PAUSED)

    def get_plan_for_execution(self, plan_id: str) -> Plan | None:
        """Get a plan ready for execution.

        Args:
            plan_id: The plan ID

        Returns:
            The plan if ready for execution, None otherwise
        """
        plan = self.storage.load_plan(plan_id)
        if plan is None:
            return None

        if plan.status != PlanStatus.APPROVED:
            return None

        # Find the first pending step
        step = plan.get_next_pending_step()
        if step is None:
            return None

        return plan
