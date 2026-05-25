from typing import List, Dict, List, Any, Optional
from uuid import UUID
from loguru import logger
import json

from ..types import Skill, Event, EventType


class SkillLibrary:
    def __init__(self, cache_size: int = 100, event_bus=None):
        self._skills: Dict[str, Skill] = {}
        self._categories: Dict[str, List[str]] = {}
        self._cache: Dict[str, Any] = {}
        self._cache_size = cache_size
        self._event_bus = event_bus
        logger.info("SkillLibrary initialized")

    def add_skill(self, skill: Skill) -> None:
        self._skills[skill.name] = skill

        if skill.category not in self._categories:
            self._categories[skill.category] = []
        if skill.name not in self._categories[skill.category]:
            self._categories[skill.category].append(skill.name)

        if self._event_bus:
            self._event_bus.publish(
                Event(
                    type=EventType.LOG,
                    payload={"message": f"Skill added: {skill.name}", "category": skill.category},
                    source="skill_library",
                )
            )

        logger.info(f"Skill added: {skill.name}")

    def get_skill(self, name: str) -> Optional[Skill]:
        if name in self._cache:
            return self._cache[name]

        skill = self._skills.get(name)
        if skill:
            self._update_cache(name, skill)

        return skill

    def _update_cache(self, name: str, skill: Skill) -> None:
        if len(self._cache) >= self._cache_size:
            oldest_key = next(iter(self._cache))
            del self._cache[oldest_key]

        self._cache[name] = skill

    def remove_skill(self, name: str) -> bool:
        if name in self._skills:
            skill = self._skills.pop(name)

            if skill.category in self._categories:
                self._categories[skill.category].remove(name)

            if name in self._cache:
                del self._cache[name]

            logger.info(f"Skill removed: {name}")
            return True
        return False

    def list_skills(self, category: Optional[str] = None) -> List[Skill]:
        if category:
            skill_names = self._categories.get(category, [])
            return [self._skills[name] for name in skill_names]
        return list(self._skills.values())

    def get_categories(self) -> List[str]:
        return list(self._categories.keys())

    def validate_schema(self, skill_name: str, args: Dict[str, Any]) -> bool:
        skill = self.get_skill(skill_name)
        if not skill:
            return False

        schema = skill.schema
        if not schema:
            return True

        properties = schema.get("properties", {})
        required = schema.get("required", [])

        for prop_name in required:
            if prop_name not in args:
                logger.warning(f"Missing required property: {prop_name}")
                return False

        for arg_name, arg_value in args.items():
            if arg_name in properties:
                prop_type = properties[arg_name].get("type")
                if prop_type:
                    if prop_type == "string" and not isinstance(arg_value, str):
                        logger.warning(f"Property {arg_name} should be string")
                        return False
                    elif prop_type == "integer" and not isinstance(arg_value, int):
                        logger.warning(f"Property {arg_name} should be integer")
                        return False
                    elif prop_type == "boolean" and not isinstance(arg_value, bool):
                        logger.warning(f"Property {arg_name} should be boolean")
                        return False

        return True

    def load_from_json(self, json_path: str) -> None:
        try:
            with open(json_path, "r") as f:
                data = json.load(f)

            for skill_data in data.get("skills", []):
                skill = Skill(
                    name=skill_data["name"],
                    description=skill_data.get("description", ""),
                    schema=skill_data.get("schema", {}),
                    handler=skill_data.get("handler", ""),
                    category=skill_data.get("category", "general"),
                    version=skill_data.get("version", "1.0.0"),
                )
                self.add_skill(skill)

            logger.info(f"Loaded {len(data.get('skills', []))} skills from {json_path}")
        except Exception as e:
            logger.error(f"Failed to load skills from {json_path}: {e}")

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_skills": len(self._skills),
            "categories": len(self._categories),
            "cached_skills": len(self._cache),
        }
