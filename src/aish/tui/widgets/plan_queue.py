"""Plan queue widget for TUI."""

from rich.text import Text

from aish.tui.types import PlanQueueState, StepStatus


class PlanQueueWidget:
    """Widget for displaying plan task queue in TUI."""

    def __init__(self, max_visible: int = 5):
        """Initialize plan queue widget.

        Args:
            max_visible: Maximum number of steps to display
        """
        self.max_visible = max_visible
        self._status_icons = {
            StepStatus.PENDING: "○",
            StepStatus.IN_PROGRESS: "◐",
            StepStatus.COMPLETED: "[green]✓[/green]",
            StepStatus.SKIPPED: "[dim]⊘[/dim]",
            StepStatus.FAILED: "[red]✗[/red]",
        }

    def render(self, queue_state: PlanQueueState) -> Text:
        """Render plan queue as formatted text.

        Args:
            queue_state: Current plan queue state

        Returns:
            Rich Text object with formatted queue display
        """
        text = Text()

        if not queue_state.is_visible or not queue_state.steps:
            return text

        # Add plan title if available
        if queue_state.plan_title:
            text.append(f"Plan: {queue_state.plan_title}", style="bold cyan")
            text.append("\n")

        # Get visible steps (around current step)
        visible_steps = self._get_visible_steps(queue_state)

        for step_data in visible_steps:
            step_num = step_data.get("number", 0)
            step_title = step_data.get("title", "")
            step_status = step_data.get("status", StepStatus.PENDING)

            # Get icon and style
            icon = self._status_icons.get(step_status, "?")
            style = self._get_step_style(step_status)

            # Highlight current step
            is_current = step_num == queue_state.current_step
            if is_current:
                style += " bold"

            # Format: "○ Step 1: Title"
            text.append(f"{icon} Step {step_num}: {step_title}", style=style)
            text.append("\n")

        # Add progress summary
        completed, total, percent = queue_state.get_progress_summary()
        if total > 0:
            progress_style = "green" if percent == 100 else "yellow"
            text.append(f"Progress: {completed}/{total} ({percent}%)", style=progress_style)

        return text

    def _get_visible_steps(self, queue_state: PlanQueueState) -> list[dict]:
        """Get visible steps centered around current step.

        Args:
            queue_state: Current plan queue state

        Returns:
            List of step dictionaries that should be visible
        """
        steps = queue_state.steps
        current = queue_state.current_step

        if len(steps) <= self.max_visible:
            return steps

        # Calculate window around current step
        half_window = self.max_visible // 2
        start_idx = max(0, current - half_window - 1)  # -1 because steps are 1-indexed
        end_idx = min(len(steps), start_idx + self.max_visible)

        # Adjust if we're near the end
        if end_idx - start_idx < self.max_visible:
            start_idx = max(0, end_idx - self.max_visible)

        return steps[start_idx:end_idx]

    def _get_step_style(self, status: StepStatus) -> str:
        """Get text style for step status.

        Args:
            status: Step status

        Returns:
            Rich style string
        """
        return {
            StepStatus.PENDING: "dim",
            StepStatus.IN_PROGRESS: "yellow",
            StepStatus.COMPLETED: "green",
            StepStatus.SKIPPED: "dim",
            StepStatus.FAILED: "red",
        }.get(status, "")

    def render_compact(self, queue_state: PlanQueueState) -> Text:
        """Render compact single-line progress indicator.

        Args:
            queue_state: Current plan queue state

        Returns:
            Rich Text object with compact progress display
        """
        text = Text()

        if not queue_state.is_visible or not queue_state.steps:
            return text

        completed, total, percent = queue_state.get_progress_summary()

        if total > 0:
            # Progress bar style
            bar_width = 20
            filled = int(bar_width * completed / total)
            bar = "█" * filled + "░" * (bar_width - filled)

            text.append(f"[Plan: {queue_state.plan_title or 'Unknown'}] ", style="cyan")
            text.append(f"[{bar}]", style="yellow")
            text.append(f" {completed}/{total} ({percent}%)", style="bold")

        return text
