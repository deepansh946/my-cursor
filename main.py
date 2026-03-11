import os
from langchain_core.load import dumps, loads
import langchain
from langchain.chat_models import init_chat_model
from deepagents import create_deep_agent
from pathlib import Path

from read_tool import ReadAndWriteTool

langchain.debug = True


prompt = """
Hello your name is Enigma, you are a helpful coding assistant. Whenever any file is provided to you, you will analyze the file and give 3 bug fixes for the file.

Tools Usage Instructions:
- When asked to do anything with a file, you will use the ReadAndWriteTool tool to read or write the file.
-When fixing code you MUST:
1. read the file
2. modify the contents
3. write the full updated file using write_file
"""


def main():
    model = init_chat_model(model="google_genai:gemini-2.5-flash-lite")
    agent = create_deep_agent(
        model=model,
        name="Enigma",
        tools=[
            ReadAndWriteTool(),
        ],
        system_prompt=prompt,
    )

    print("Hello from my-cursor!")

    response = agent.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": "Please fix the bugs in the test.py file present.",
                }
            ],
        }
    )

    # print(dumps(response, pretty=True))

    for message in response["messages"]:
        print(message.content)


if __name__ == "__main__":
    main()
