"""Storage layer for Plan mode using SQLite and Markdown files."""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from aish.config import get_default_aish_data_dir
from aish.plans.models import Plan, PlanStep, StepStatus


class PlanStorage:
    """Storage for plans using SQLite database and markdown files."""

    def __init__(self, data_dir: Path | None = None):
        """Initialize plan storage.

        Args:
            data_dir: Base directory for storing plans. Defaults to XDG data home.
        """
        if data_dir is None:
            data_dir = get_default_aish_data_dir()

        self.data_dir = data_dir / "plans"
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.db_path = self.data_dir / "plans.db"
        self._init_db()

    def _init_db(self) -> None:
        """Initialize SQLite database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS plans (
                    plan_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    description TEXT,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    author TEXT NOT NULL,
                    context TEXT,
                    file_path TEXT UNIQUE,
                    current_step INTEGER DEFAULT 1
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS plan_steps (
                    step_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    plan_id TEXT NOT NULL,
                    step_number INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT,
                    commands TEXT,
                    expected_outcome TEXT,
                    verification TEXT,
                    status TEXT NOT NULL,
                    started_at TEXT,
                    completed_at TEXT,
                    error_message TEXT,
                    dependencies TEXT,
                    FOREIGN KEY (plan_id) REFERENCES plans(plan_id) ON DELETE CASCADE
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_plan_steps_plan_id ON plan_steps(plan_id)"
            )

    def save_plan(self, plan: Plan) -> None:
        """Save plan to database and markdown file.

        Args:
            plan: The plan to save
        """
        # Set file_path before database insert to avoid UNIQUE constraint conflicts
        md_path = self.data_dir / f"{plan.plan_id}.md"
        if not plan.file_path:
            plan.file_path = str(md_path)

        # Update timestamp
        plan.updated_at = datetime.now()

        with sqlite3.connect(self.db_path) as conn:
            # Save to database
            conn.execute(
                """
                INSERT OR REPLACE INTO plans
                (plan_id, title, description, status, created_at, updated_at, author, context, file_path, current_step)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    plan.plan_id,
                    plan.title,
                    plan.description,
                    plan.status.value,
                    plan.created_at.isoformat(),
                    plan.updated_at.isoformat(),
                    plan.author,
                    plan.context,
                    plan.file_path,
                    plan.current_step,
                ),
            )

            # Delete existing steps
            conn.execute(
                "DELETE FROM plan_steps WHERE plan_id = ?",
                (plan.plan_id,),
            )

            # Insert steps
            for step in plan.steps:
                # StepStatus is a str enum, so step.status is already a string
                status_value = step.status if isinstance(step.status, str) else step.status.value

                conn.execute(
                    """
                    INSERT INTO plan_steps
                    (plan_id, step_number, title, description, commands, expected_outcome, verification,
                     status, started_at, completed_at, error_message, dependencies)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        plan.plan_id,
                        step.number,
                        step.title,
                        step.description,
                        json.dumps(step.commands),
                        step.expected_outcome,
                        step.verification,
                        status_value,
                        step.started_at.isoformat() if step.started_at else None,
                        step.completed_at.isoformat() if step.completed_at else None,
                        step.error_message,
                        json.dumps(step.dependencies),
                    ),
                )

        # Save to markdown file (outside of db transaction)
        self._save_markdown(plan)

    def load_plan(self, plan_id: str) -> Plan | None:
        """Load plan from database.

        Args:
            plan_id: The plan ID to load

        Returns:
            The plan if found, None otherwise
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                SELECT plan_id, title, description, status, created_at, updated_at, author, context, file_path, current_step
                FROM plans WHERE plan_id = ?
                """,
                (plan_id,),
            )
            row = cursor.fetchone()

            if row is None:
                return None

            # Load steps
            step_cursor = conn.execute(
                """
                SELECT step_number, title, description, commands, expected_outcome, verification,
                       status, started_at, completed_at, error_message, dependencies
                FROM plan_steps WHERE plan_id = ? ORDER BY step_number
                """,
                (plan_id,),
            )

            steps = []
            for step_row in step_cursor.fetchall():
                # Convert status string to StepStatus enum
                step_status = StepStatus(step_row[6]) if step_row[6] else StepStatus.PENDING

                step = PlanStep(
                    number=step_row[0],
                    title=step_row[1],
                    description=step_row[2] or "",
                    commands=json.loads(step_row[3]) if step_row[3] else [],
                    expected_outcome=step_row[4] or "",
                    verification=step_row[5] or "",
                    status=step_status,
                    started_at=datetime.fromisoformat(step_row[7]) if step_row[7] else None,
                    completed_at=datetime.fromisoformat(step_row[8]) if step_row[8] else None,
                    error_message=step_row[9] or "",
                    dependencies=json.loads(step_row[10]) if step_row[10] else [],
                )
                steps.append(step)

            from aish.plans.models import PlanStatus

            plan = Plan(
                plan_id=row[0],
                title=row[1],
                description=row[2],
                status=PlanStatus(row[3]),
                steps=steps,
                context=row[7] or "",
                author=row[6] or "",
                created_at=datetime.fromisoformat(row[4]),
                updated_at=datetime.fromisoformat(row[5]),
                current_step=row[9] or 1,
                file_path=row[8] or "",
            )

            return plan

    def list_plans(
        self,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """List plans with optional filtering.

        Args:
            status: Filter by plan status
            limit: Maximum number of plans to return
            offset: Offset for pagination

        Returns:
            List of plan summary dictionaries
        """
        with sqlite3.connect(self.db_path) as conn:
            if status:
                cursor = conn.execute(
                    """
                    SELECT plan_id, title, status, created_at, updated_at, current_step,
                           (SELECT COUNT(*) FROM plan_steps WHERE plan_id = p.plan_id) as total_steps,
                           (SELECT COUNT(*) FROM plan_steps WHERE plan_id = p.plan_id AND status = 'completed') as completed_steps
                    FROM plans p
                    WHERE status = ?
                    ORDER BY updated_at DESC
                    LIMIT ? OFFSET ?
                    """,
                    (status, limit, offset),
                )
            else:
                cursor = conn.execute(
                    """
                    SELECT plan_id, title, status, created_at, updated_at, current_step,
                           (SELECT COUNT(*) FROM plan_steps WHERE plan_id = p.plan_id) as total_steps,
                           (SELECT COUNT(*) FROM plan_steps WHERE plan_id = p.plan_id AND status = 'completed') as completed_steps
                    FROM plans p
                    ORDER BY updated_at DESC
                    LIMIT ? OFFSET ?
                    """,
                    (limit, offset),
                )

            plans = []
            for row in cursor.fetchall():
                plans.append(
                    {
                        "plan_id": row[0],
                        "title": row[1],
                        "status": row[2],
                        "created_at": row[3],
                        "updated_at": row[4],
                        "current_step": row[5],
                        "total_steps": row[6],
                        "completed_steps": row[7],
                    }
                )

            return plans

    def delete_plan(self, plan_id: str) -> bool:
        """Delete plan from storage.

        Args:
            plan_id: The plan ID to delete

        Returns:
            True if deleted, False if not found
        """
        file_path_to_delete = None

        with sqlite3.connect(self.db_path) as conn:
            # First get the file path to delete markdown
            cursor = conn.execute(
                "SELECT file_path FROM plans WHERE plan_id = ?",
                (plan_id,),
            )
            row = cursor.fetchone()

            if row and row[0]:
                file_path_to_delete = row[0]

            # Delete from database (cascade will delete steps)
            delete_cursor = conn.execute("DELETE FROM plans WHERE plan_id = ?", (plan_id,))
            deleted = delete_cursor.rowcount > 0

        # Delete markdown file (outside of db transaction)
        if deleted and file_path_to_delete:
            try:
                Path(file_path_to_delete).unlink(missing_ok=True)
            except (OSError, IOError):
                pass

        return deleted

    def _save_markdown(self, plan: Plan) -> None:
        """Save plan as markdown file.

        Args:
            plan: The plan to save
        """
        md_path = self.data_dir / f"{plan.plan_id}.md"

        # Check if this is a new plan (no file_path set)
        if not plan.file_path:
            plan.file_path = str(md_path)

        # Write markdown content with YAML frontmatter
        lines = [
            "---",
            f"plan_id: {plan.plan_id}",
            f"status: {plan.status.value}",
            f"current_step: {plan.current_step}",
            f"created_at: {plan.created_at.isoformat()}",
            f"updated_at: {plan.updated_at.isoformat()}",
            "---",
            "",
            plan.to_markdown(),
        ]

        with open(md_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

    def get_markdown_path(self, plan_id: str) -> Path:
        """Get the markdown file path for a plan.

        Args:
            plan_id: The plan ID

        Returns:
            Path to the markdown file
        """
        return self.data_dir / f"{plan_id}.md"
