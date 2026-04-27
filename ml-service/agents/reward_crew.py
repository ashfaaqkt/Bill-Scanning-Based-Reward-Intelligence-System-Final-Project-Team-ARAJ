"""
Reward Recommendation Crew — Owner: Jyoti Kataria
CrewAI multi-agent pipeline for generating personalised reward recommendations.
Called after a successful (non-fraudulent) receipt upload.
"""

# TODO (Jyoti): Uncomment and implement agents once CrewAI is confirmed working.
# from crewai import Agent, Task, Crew
# from langchain_anthropic import ChatAnthropic


# TODO (Jyoti): Initialise LLM
# llm = ChatAnthropic(model="claude-sonnet-4-6")


# TODO (Jyoti): Define 3 agents
#
# profile_reader = Agent(
#     role="Profile Reader",
#     goal="Read and summarise the user's spending profile and category preferences.",
#     backstory="Customer analytics expert who understands long-term spending behaviour.",
#     llm=llm,
#     verbose=True
# )
#
# market_analyst = Agent(
#     role="Market Analyst",
#     goal="Identify current reward offers and promotions relevant to the user's categories.",
#     backstory="Retail market specialist who tracks promotional campaigns and partner offers.",
#     llm=llm,
#     verbose=True
# )
#
# recommender = Agent(
#     role="Recommender",
#     goal="Match user profile to best available offers and rank them by personalisation score.",
#     backstory="Personalisation engine expert who balances relevance, novelty, and value.",
#     llm=llm,
#     verbose=True
# )


# TODO (Jyoti): Define tasks and wire them to agents
# task_profile = Task(description="...", agent=profile_reader)
# task_market = Task(description="...", agent=market_analyst)
# task_recommend = Task(description="...", agent=recommender, context=[task_profile, task_market])


# TODO (Jyoti): Assemble crew
# reward_crew = Crew(
#     agents=[profile_reader, market_analyst, recommender],
#     tasks=[task_profile, task_market, task_recommend],
#     verbose=True
# )


def recommend(user_id: str, receipt_context: dict) -> dict:
    """
    Placeholder — returns empty recommendations.
    TODO (Jyoti): replace with reward_crew.kickoff(inputs={...}) once agents are defined.
    Returns: { "recommendations": list, "reasoning": str }
    """
    return {
        "recommendations": [],
        "reasoning": "CrewAI reward crew not yet implemented.",
        "status": "placeholder"
    }
