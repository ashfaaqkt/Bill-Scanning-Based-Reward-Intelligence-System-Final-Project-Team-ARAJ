"""
Fraud Investigation Crew — Owner: Ashfaaq Feroz Muhammad
CrewAI multi-agent pipeline for deep fraud investigation on flagged receipts.
Called only when fraud.score() returns a score above the threshold (e.g. > 0.5).
"""

# TODO (Ashfaaq): Uncomment and implement agents once CrewAI is confirmed working.
# from crewai import Agent, Task, Crew
# from langchain_anthropic import ChatAnthropic


# TODO (Ashfaaq): Initialise LLM
# llm = ChatAnthropic(model="claude-sonnet-4-6")


# TODO (Ashfaaq): Define 4 agents
#
# image_analyst = Agent(
#     role="Image Analyst",
#     goal="Inspect the receipt image for visual signs of tampering, digital editing, or blur.",
#     backstory="Expert in digital forensics and image manipulation detection.",
#     llm=llm,
#     verbose=True
# )
#
# metadata_agent = Agent(
#     role="Metadata Agent",
#     goal="Analyse receipt metadata: total amount, date, merchant, and known patterns.",
#     backstory="Specialist in transactional data consistency and anomaly detection.",
#     llm=llm,
#     verbose=True
# )
#
# pattern_analyst = Agent(
#     role="Pattern Analyst",
#     goal="Compare this receipt against the user's historical spending patterns.",
#     backstory="Behavioural analytics expert who identifies unusual user activity.",
#     llm=llm,
#     verbose=True
# )
#
# fraud_judge = Agent(
#     role="Fraud Judge",
#     goal="Synthesise all agent findings and deliver a final fraud verdict with justification.",
#     backstory="Senior fraud investigator with final decision authority.",
#     llm=llm,
#     verbose=True
# )


# TODO (Ashfaaq): Define tasks and wire them to agents
# task_image = Task(description="...", agent=image_analyst)
# task_metadata = Task(description="...", agent=metadata_agent)
# task_pattern = Task(description="...", agent=pattern_analyst)
# task_judge = Task(description="...", agent=fraud_judge, context=[task_image, task_metadata, task_pattern])


# TODO (Ashfaaq): Assemble crew
# fraud_crew = Crew(
#     agents=[image_analyst, metadata_agent, pattern_analyst, fraud_judge],
#     tasks=[task_image, task_metadata, task_pattern, task_judge],
#     verbose=True
# )


def investigate(image_path: str, metadata: dict, fraud_signals: dict) -> dict:
    """
    Placeholder — returns a stub verdict.
    TODO (Ashfaaq): replace with fraud_crew.kickoff(inputs={...}) once agents are defined.
    Returns: { "verdict": str, "confidence": float, "reasoning": str }
    """
    return {
        "verdict": "under_review",
        "confidence": 0.0,
        "reasoning": "CrewAI fraud crew not yet implemented.",
        "status": "placeholder"
    }
