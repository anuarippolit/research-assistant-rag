import anthropic
from app.config import settings

client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

# system = standing rules from the developer (role, format, constraints); user = this turn's actual input (sources + question)
def ask_claude(system: str, user: str, max_tokens = 2048) -> str:
    response = client.messages.create(
        model=settings.chat_model,
        max_tokens=max_tokens,
        system = system, 
        messages = [{"role": "user", "content": user}],
        output_config = {"effort" : "low"}
    )

    return "".join(block.text for block in response.content if block.type == "text")