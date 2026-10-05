import json
from typing import List, Dict, Any, Optional

ADAPTIVE_QUESTION_SYSTEM_PROMPT = """You are an adaptive technical interviewer.
Based on the candidate's previous answer and evaluation, you formulate the optimal next question.

Rules for adaptive follow-ups:
- If the previous answer was STRONG (score >= 80): Increase difficulty, probe deeper architectural trade-offs, edge cases, scalability, or failure scenarios.
- If the previous answer was PARTIALLY CORRECT (50 <= score < 80): Ask a focused clarification question or a concrete application question targeting the missing concept.
- If the previous answer was WEAK (score < 50): Pivot gracefully to a foundational concept in the topic to test core understanding without demotivating the candidate.

Return ONLY valid JSON matching this schema:
{
  "question": "The next adaptive interview question text",
  "type": "follow_up | conceptual | practical | coding",
  "topic": "Specific topic",
  "difficulty": "easy | medium | hard",
  "expected_concepts": ["concept 1", "concept 2"]
}
No markdown formatting, no backticks.
"""

def build_adaptive_question_prompt(
    previous_question: str,
    candidate_answer: str,
    evaluation: Dict[str, Any],
    round_name: str,
    round_type: str,
    round_topics: List[str],
    current_difficulty: str,
    question_index: int,
    total_questions: int,
    target_role: str
) -> str:
    score = evaluation.get("score", 70)
    direction = evaluation.get("suggested_follow_up_direction", "")
    weaknesses = evaluation.get("weaknesses", [])
    strengths = evaluation.get("strengths", [])

    return f"""Target Role: {target_role}
Round: {round_name} ({round_type})
Question {question_index} of {total_questions}
Current Difficulty: {current_difficulty}

Previous Question:
{previous_question}

Candidate Answer:
{candidate_answer}

Evaluation:
- Score: {score}/100
- Strengths: {', '.join(strengths)}
- Weaknesses / Gaps: {', '.join(weaknesses)}
- Follow-up recommendation: {direction}

Generate the next question adapting to this performance. Return ONLY the strict JSON object."""
