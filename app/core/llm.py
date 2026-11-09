import base64

import anthropic
from app.config import settings

client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

# system = standing rules from the developer (role, format, constraints); user = this turn's actual input (sources + question)
def ask_claude(system: str, user: str, max_tokens = 2048, image_png: bytes | None = None) -> str:
    content = user
    if image_png is not None:
        # with an image, "content" becomes a list of blocks: the picture (base64) first, then the text
        content = [
            {"type": "image", "source": {"type": "base64", "media_type": "image/png",
                                         "data": base64.standard_b64encode(image_png).decode()}},
            {"type": "text", "text": user},
        ]
    response = client.messages.create(
        model=settings.chat_model,
        max_tokens=max_tokens,
        system = system,
        messages = [{"role": "user", "content": content}],
        output_config = {"effort" : "low"}
    )

    return "".join(block.text for block in response.content if block.type == "text")