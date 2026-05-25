from typing import List, Dict, List, Any, Optional
from loguru import logger
import os
import re

from ..types import Skill


class SkillSystem:
    def __init__(self, skill_dir: str = "./skills"):
        self._skill_dir = skill_dir
        self._skills: Dict[str, Skill] = {}
        os.makedirs(skill_dir, exist_ok=True)
        logger.info("SkillSystem initialized")

    def scan(self) -> None:
        self._skills.clear()

        for filename in os.listdir(self._skill_dir):
            if filename.endswith(".md"):
                filepath = os.path.join(self._skill_dir, filename)
                skill = self._parse_skill_file(filepath)
                if skill:
                    self._skills[skill.name] = skill

        logger.info(f"Scanned {len(self._skills)} skills from {self._skill_dir}")

    def _parse_skill_file(self, filepath: str) -> Optional[Skill]:
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()

            metadata = self._extract_metadata(content)

            if not metadata.get("name"):
                name = os.path.splitext(os.path.basename(filepath))[0]
                metadata["name"] = name

            schema = self._extract_schema(content)

            return Skill(
                name=metadata.get("name", ""),
                description=metadata.get("description", ""),
                schema=schema,
                handler=metadata.get("handler", ""),
                category=metadata.get("category", "general"),
                version=metadata.get("version", "1.0.0"),
            )
        except Exception as e:
            logger.error(f"Failed to parse skill file {filepath}: {e}")
            return None

    def _extract_metadata(self, content: str) -> Dict[str, str]:
        metadata = {}
        lines = content.split("\n")

        in_metadata = False
        for line in lines:
            if line.startswith("---"):
                in_metadata = not in_metadata
                continue

            if in_metadata:
                parts = line.split(":", 1)
                if len(parts) == 2:
                    key = parts[0].strip()
                    value = parts[1].strip()
                    metadata[key] = value

        return metadata

    def _extract_schema(self, content: str) -> Dict[str, Any]:
        match = re.search(r"```json(.*?)```", content, re.DOTALL)
        if match:
            try:
                import json

                return json.loads(match.group(1))
            except json.JSONDecodeError:
                logger.warning("Invalid JSON schema in skill file")

        return {}

    def get_skill(self, name: str) -> Optional[Skill]:
        return self._skills.get(name)

    def list_skills(self) -> List[Skill]:
        return list(self._skills.values())

    def add_skill(self, skill: Skill) -> None:
        self._skills[skill.name] = skill
        self._write_skill_file(skill)
        logger.info(f"Skill added: {skill.name}")

    def _write_skill_file(self, skill: Skill) -> None:
        filepath = os.path.join(self._skill_dir, f"{skill.name}.md")

        content = f"""---
name: {skill.name}
description: {skill.description}
handler: {skill.handler}
category: {skill.category}
version: {skill.version}
---

## Schema

```json
{self._format_schema(skill.schema)}
```

## Description

{skill.description}
"""

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

    def _format_schema(self, schema: Dict[str, Any]) -> str:
        import json

        return json.dumps(schema, indent=2, ensure_ascii=False)

    def remove_skill(self, name: str) -> bool:
        if name in self._skills:
            del self._skills[name]
            filepath = os.path.join(self._skill_dir, f"{name}.md")
            if os.path.exists(filepath):
                os.remove(filepath)
            logger.info(f"Skill removed: {name}")
            return True
        return False
