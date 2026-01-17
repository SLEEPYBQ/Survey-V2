"""
Question configuration loader for Survey-PQE.
Loads question definitions from YAML files and provides derived data structures.
"""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml


@dataclass
class Question:
    """Represents a single survey question."""
    id: str
    display_name: str
    prompt: str


@dataclass
class QuestionConfig:
    """Loaded question configuration with derived data structures."""
    survey_name: str
    survey_description: str
    questions: list[Question] = field(default_factory=list)

    def __post_init__(self):
        self._question_ids = [q.id for q in self.questions]
        self._id_to_display = {q.id: q.display_name for q in self.questions}
        self._display_to_id = {q.display_name: q.id for q in self.questions}

    @property
    def question_ids(self) -> list[str]:
        """List of question IDs in order. Replaces QUESTION_IDS."""
        return self._question_ids

    @property
    def question_patterns(self) -> list[tuple[str, str]]:
        """List of (display_name, id) tuples. Replaces QUESTION_PATTERNS."""
        return [(q.display_name, q.id) for q in self.questions]

    @property
    def id_to_display_name(self) -> dict[str, str]:
        """Mapping from question ID to display name."""
        return self._id_to_display

    @property
    def display_name_to_id(self) -> dict[str, str]:
        """Mapping from display name to question ID."""
        return self._display_to_id

    def get_prompts_dict(self) -> dict[str, str]:
        """Get ID to prompt mapping for dynamic prompt generation."""
        return {q.id: q.prompt for q in self.questions}


class QuestionLoaderError(Exception):
    """Raised when question configuration loading fails."""
    pass


def validate_question_id(question_id: str) -> bool:
    """Validate that a question ID is a valid Python identifier."""
    return bool(re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', question_id))


def load_questions(yaml_path: str | Path) -> QuestionConfig:
    """
    Load question configuration from a YAML file.

    Args:
        yaml_path: Path to the YAML configuration file

    Returns:
        QuestionConfig object with loaded questions

    Raises:
        QuestionLoaderError: If file not found, malformed YAML, or validation fails
    """
    yaml_path = Path(yaml_path)

    # File existence check
    if not yaml_path.exists():
        raise QuestionLoaderError(f"Question config file not found: {yaml_path}")

    if yaml_path.suffix not in ('.yaml', '.yml'):
        raise QuestionLoaderError(f"Question config must be a YAML file: {yaml_path}")

    # Load YAML
    try:
        with open(yaml_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise QuestionLoaderError(f"Invalid YAML syntax in {yaml_path}: {e}")

    if not data:
        raise QuestionLoaderError(f"Empty configuration file: {yaml_path}")

    # Extract metadata
    survey = data.get('survey', {})
    survey_name = survey.get('name', yaml_path.stem)
    survey_description = survey.get('description', '')

    # Parse questions
    questions_data = data.get('questions', [])
    if not questions_data:
        raise QuestionLoaderError(f"No questions defined in {yaml_path}")

    questions = []
    seen_ids = set()
    seen_display_names = set()

    for i, q_data in enumerate(questions_data):
        if not isinstance(q_data, dict):
            raise QuestionLoaderError(
                f"Question {i+1} must be a mapping, got {type(q_data).__name__}"
            )

        q_id = q_data.get('id')
        display_name = q_data.get('display_name')
        prompt = q_data.get('prompt')

        # Required field validation
        if not q_id:
            raise QuestionLoaderError(f"Question {i+1} missing required field 'id'")
        if not display_name:
            raise QuestionLoaderError(f"Question '{q_id}' missing 'display_name'")
        if not prompt:
            raise QuestionLoaderError(f"Question '{q_id}' missing 'prompt'")

        # ID format validation
        if not validate_question_id(q_id):
            raise QuestionLoaderError(
                f"Question ID '{q_id}' is invalid "
                "(must start with letter/underscore, contain only alphanumeric and underscore)"
            )

        # Duplicate checks
        if q_id in seen_ids:
            raise QuestionLoaderError(f"Duplicate question ID: '{q_id}'")
        if display_name in seen_display_names:
            raise QuestionLoaderError(f"Duplicate display name: '{display_name}'")

        seen_ids.add(q_id)
        seen_display_names.add(display_name)

        questions.append(Question(
            id=q_id,
            display_name=display_name,
            prompt=prompt.strip()
        ))

    return QuestionConfig(
        survey_name=survey_name,
        survey_description=survey_description,
        questions=questions
    )


def find_default_config() -> Optional[Path]:
    """
    Find a default question config file.

    Searches: questions/default.yaml, then alphabetically first .yaml file.
    """
    questions_dir = Path(__file__).parent / 'questions'

    if not questions_dir.exists():
        return None

    default_path = questions_dir / 'default.yaml'
    if default_path.exists():
        return default_path

    yaml_files = list(questions_dir.glob('*.yaml')) + list(questions_dir.glob('*.yml'))
    return sorted(yaml_files)[0] if yaml_files else None


# Global config singleton
_loaded_config: Optional[QuestionConfig] = None


def get_config() -> QuestionConfig:
    """Get the currently loaded question configuration."""
    if _loaded_config is None:
        raise RuntimeError(
            "Question configuration not loaded. "
            "Call load_questions() and set_config() first."
        )
    return _loaded_config


def set_config(config: QuestionConfig):
    """Set the global question configuration."""
    global _loaded_config
    _loaded_config = config
