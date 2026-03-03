"""Async AI Data Agent - terminal chat interface.

Run from db_code directory:
  cd db_code && python -m db_agent.main
"""

import asyncio

from db_connect import init as init_db
from tortoise import Tortoise

from db_agent.agent import create_db_agent


async def main() -> None:
    """Interactive chat loop for the AI Data Agent."""
    print("Initializing database...")
    await init_db()

    print("Loading agent...")
    agent = create_db_agent()

    # Conversation history across turns (messages list returned by the agent)
    history = []

    print("\nAI Data Agent ready. Type your question and press Enter. "
          "Type 'quit' or 'exit' to stop.\n")

    while True:
        try:
            user_input = await asyncio.to_thread(input, "You: ")
        except (EOFError, KeyboardInterrupt):
            break

        user_input = user_input.strip()
        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit", "q"):
            break

        try:
            # Pass full conversation so far + new user turn
            input_state = {"messages": [*history, ("user", user_input)]}
            result = await agent.ainvoke(input_state, config={"configurable": {}})

            messages = result.get("messages", [])
            # Update history with latest messages from the agent
            if messages:
                history = messages

            last_message = messages[-1] if messages else None
            if last_message and hasattr(last_message, "content"):
                print(f"\nAgent: {last_message.content}\n")
            else:
                print(f"\nAgent: {result}\n")
        except Exception as e:
            print(f"\nError: {e}\n")

    print("Closing database connections...")
    await Tortoise.close_connections()
    print("Goodbye.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass