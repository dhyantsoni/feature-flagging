"""
Feature Scheduling Module

Enables time-based feature flag activation and deactivation.
Supports one-time, date range, and recurring (cron) schedules.
"""

import re
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List, Tuple
import logging

logger = logging.getLogger(__name__)


class CronParser:
    """Simple cron expression parser for recurring schedules."""

    WEEKDAYS = {"sun": 0, "mon": 1, "tue": 2, "wed": 3, "thu": 4, "fri": 5, "sat": 6}

    @staticmethod
    def parse_field(field: str, min_val: int, max_val: int) -> List[int]:
        """Parse a single cron field into list of matching values."""
        values = set()

        for part in field.split(","):
            part = part.strip().lower()

            # Handle day of week names
            for name, num in CronParser.WEEKDAYS.items():
                part = part.replace(name, str(num))

            # Handle * (all values)
            if part == "*":
                values.update(range(min_val, max_val + 1))
                continue

            # Handle */n (every n)
            if part.startswith("*/"):
                step = int(part[2:])
                values.update(range(min_val, max_val + 1, step))
                continue

            # Handle ranges (e.g., 1-5)
            if "-" in part and "/" not in part:
                start, end = part.split("-")
                values.update(range(int(start), int(end) + 1))
                continue

            # Handle range with step (e.g., 1-5/2)
            if "-" in part and "/" in part:
                range_part, step = part.split("/")
                start, end = range_part.split("-")
                values.update(range(int(start), int(end) + 1, int(step)))
                continue

            # Handle single value
            try:
                values.add(int(part))
            except ValueError:
                pass

        return sorted(values)

    @staticmethod
    def matches(cron_expr: str, dt: datetime) -> bool:
        """
        Check if datetime matches cron expression.

        Cron format: minute hour day_of_month month day_of_week
        Example: "0 9 * * 1-5" = 9:00 AM on weekdays
        """
        try:
            parts = cron_expr.strip().split()
            if len(parts) != 5:
                return False

            minute, hour, day, month, dow = parts

            minutes = CronParser.parse_field(minute, 0, 59)
            hours = CronParser.parse_field(hour, 0, 23)
            days = CronParser.parse_field(day, 1, 31)
            months = CronParser.parse_field(month, 1, 12)
            weekdays = CronParser.parse_field(dow, 0, 6)

            return (
                dt.minute in minutes and
                dt.hour in hours and
                (dt.day in days or day == "*") and
                dt.month in months and
                (dt.weekday() in weekdays or dow == "*")  # Python weekday: Mon=0
            )
        except Exception as e:
            logger.debug(f"Error parsing cron expression '{cron_expr}': {e}")
            return False


class Schedule:
    """Represents a feature schedule."""

    TYPE_ONE_TIME = "one_time"
    TYPE_DATE_RANGE = "date_range"
    TYPE_RECURRING = "recurring"

    def __init__(self, config: Dict[str, Any]):
        self.id = config.get("id")
        self.feature_name = config.get("feature_name", "")
        self.ruleset_name = config.get("ruleset_name")  # None = all rulesets
        self.client_id = config.get("client_id")  # None = all clients
        self.schedule_type = config.get("schedule_type", self.TYPE_DATE_RANGE)
        self.timezone = config.get("timezone", "UTC")
        self.cron_expression = config.get("cron_expression")
        self.is_active = config.get("is_active", True)
        self.enabled_during_schedule = config.get("enabled_during_schedule", True)
        self.priority = config.get("priority", 0)
        self.metadata = config.get("metadata", {})

        # Parse datetime fields
        self.start_at = self._parse_datetime(config.get("start_at"))
        self.end_at = self._parse_datetime(config.get("end_at"))

    def _parse_datetime(self, value) -> Optional[datetime]:
        """Parse datetime from string or return datetime as-is."""
        if value is None:
            return None
        if isinstance(value, datetime):
            return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        if isinstance(value, str):
            try:
                dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
                return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
            except ValueError:
                return None
        return None

    def is_within_schedule(self, dt: Optional[datetime] = None) -> bool:
        """
        Check if given datetime (or now) falls within this schedule.

        Returns:
            True if within schedule
        """
        if not self.is_active:
            return False

        if dt is None:
            dt = datetime.now(timezone.utc)

        # Ensure dt is timezone-aware
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        if self.schedule_type == self.TYPE_ONE_TIME:
            # One-time: check if exactly at start_at (within 1 minute window)
            if self.start_at:
                diff = abs((dt - self.start_at).total_seconds())
                return diff <= 60  # 1 minute window

        elif self.schedule_type == self.TYPE_DATE_RANGE:
            # Date range: check if between start and end
            if self.start_at and dt < self.start_at:
                return False
            if self.end_at and dt > self.end_at:
                return False
            return True

        elif self.schedule_type == self.TYPE_RECURRING:
            # Recurring: check cron expression
            if not self.cron_expression:
                return False

            # Also check date bounds if set
            if self.start_at and dt < self.start_at:
                return False
            if self.end_at and dt > self.end_at:
                return False

            return CronParser.matches(self.cron_expression, dt)

        return False

    def get_enabled_state(self) -> bool:
        """Get whether feature should be enabled during schedule."""
        return self.enabled_during_schedule

    def applies_to(self, client_id: Optional[str], ruleset_name: Optional[str]) -> bool:
        """Check if schedule applies to given client/ruleset."""
        if self.client_id and self.client_id != client_id:
            return False
        if self.ruleset_name and self.ruleset_name != ruleset_name:
            return False
        return True


class ScheduleEngine:
    """
    Engine for evaluating feature schedules.

    Schedules are evaluated in priority order (highest first).
    First matching schedule determines feature state.
    """

    def __init__(self, supabase_client=None):
        self.supabase = supabase_client
        self.schedules: Dict[str, List[Schedule]] = {}  # feature_name -> schedules
        self._cache_loaded = False
        self._cache_time: Optional[datetime] = None
        self._cache_ttl = 60  # Refresh cache every 60 seconds

    def load_schedules_from_config(self, schedules_config: List[Dict[str, Any]]):
        """Load schedules from configuration."""
        self.schedules = {}

        for schedule_config in schedules_config:
            schedule = Schedule(schedule_config)
            feature = schedule.feature_name

            if feature not in self.schedules:
                self.schedules[feature] = []

            self.schedules[feature].append(schedule)

        # Sort by priority (descending)
        for feature in self.schedules:
            self.schedules[feature].sort(key=lambda s: s.priority, reverse=True)

    def load_schedules_from_db(self, force: bool = False):
        """Load schedules from Supabase."""
        if not self.supabase:
            return

        # Check cache validity
        now = datetime.now(timezone.utc)
        if (not force and self._cache_loaded and self._cache_time and
            (now - self._cache_time).total_seconds() < self._cache_ttl):
            return

        try:
            result = self.supabase.client.table("feature_schedules").select("*").eq(
                "is_active", True
            ).order("priority", desc=True).execute()

            if result.data:
                self.load_schedules_from_config(result.data)

            self._cache_loaded = True
            self._cache_time = now
        except Exception as e:
            logger.error(f"Error loading schedules: {e}")

    def evaluate(
        self,
        feature_name: str,
        client_id: Optional[str] = None,
        ruleset_name: Optional[str] = None,
        dt: Optional[datetime] = None
    ) -> Tuple[Optional[bool], Optional[Schedule]]:
        """
        Evaluate schedules for a feature.

        Args:
            feature_name: Feature to evaluate
            client_id: Client ID (for client-specific schedules)
            ruleset_name: Ruleset name (for ruleset-specific schedules)
            dt: Datetime to check (default: now)

        Returns:
            Tuple of (enabled_state, matching_schedule) or (None, None) if no schedule applies
        """
        self.load_schedules_from_db()

        schedules = self.schedules.get(feature_name, [])

        for schedule in schedules:
            if not schedule.applies_to(client_id, ruleset_name):
                continue

            if schedule.is_within_schedule(dt):
                return schedule.get_enabled_state(), schedule

        return None, None

    def add_schedule(self, schedule_config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Add a new schedule."""
        if self.supabase:
            try:
                result = self.supabase.client.table("feature_schedules").insert(
                    schedule_config
                ).execute()

                if result.data:
                    self.load_schedules_from_db(force=True)
                    return result.data[0]
            except Exception as e:
                logger.error(f"Error adding schedule: {e}")
        return None

    def update_schedule(self, schedule_id: str, updates: Dict[str, Any]) -> bool:
        """Update an existing schedule."""
        if self.supabase:
            try:
                self.supabase.client.table("feature_schedules").update(updates).eq(
                    "id", schedule_id
                ).execute()
                self.load_schedules_from_db(force=True)
                return True
            except Exception as e:
                logger.error(f"Error updating schedule: {e}")
        return False

    def delete_schedule(self, schedule_id: str) -> bool:
        """Delete a schedule."""
        if self.supabase:
            try:
                self.supabase.client.table("feature_schedules").delete().eq(
                    "id", schedule_id
                ).execute()
                self.load_schedules_from_db(force=True)
                return True
            except Exception as e:
                logger.error(f"Error deleting schedule: {e}")
        return False

    def list_schedules(
        self,
        feature_name: Optional[str] = None,
        active_only: bool = True
    ) -> List[Dict[str, Any]]:
        """List schedules."""
        if not self.supabase:
            return []

        try:
            query = self.supabase.client.table("feature_schedules").select("*")

            if feature_name:
                query = query.eq("feature_name", feature_name)

            if active_only:
                query = query.eq("is_active", True)

            result = query.order("priority", desc=True).execute()
            return result.data or []
        except Exception as e:
            logger.error(f"Error listing schedules: {e}")
            return []

    def get_upcoming_schedules(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get schedules starting within the next N hours."""
        if not self.supabase:
            return []

        try:
            now = datetime.now(timezone.utc)
            future = now + timedelta(hours=hours)

            result = self.supabase.client.table("feature_schedules").select("*").eq(
                "is_active", True
            ).gte("start_at", now.isoformat()).lte("start_at", future.isoformat()).execute()

            return result.data or []
        except Exception as e:
            logger.error(f"Error getting upcoming schedules: {e}")
            return []


# Global schedule engine instance
_schedule_engine: Optional[ScheduleEngine] = None


def get_schedule_engine(supabase_client=None) -> ScheduleEngine:
    """Get or create the global schedule engine."""
    global _schedule_engine
    if _schedule_engine is None:
        _schedule_engine = ScheduleEngine(supabase_client)
    return _schedule_engine
