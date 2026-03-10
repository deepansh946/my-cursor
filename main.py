import os
from langchain.chat_models import init_chat_model
from deepagents import create_deep_agent
from pathlib import Path
from langchain_community.tools.file_management import (
    WriteFileTool,
    ReadFileTool,
)


prompt = """
Hello your name is Enigma, you are a helpful coding assistant. Whenever any file is provided to you, you will analyze the file and give 3 bug fixes for the file.

When asked to read a file, you will use the ReadFileTool tool to read the file and for writing a file, you will use the WriteFileTool tool. 

Whenever you'll make changes in the file, you will do at the bottom of the file so that I can easily see the changes.
"""


def main():
    model = init_chat_model(model="google_genai:gemini-2.5-flash-lite")
    agent = create_deep_agent(
        model=model,
        name="Enigma",
        tools=[
            ReadFileTool(),
            WriteFileTool(),
        ],
        system_prompt=prompt,
    )
    location = os.path.join(os.path.dirname(__file__), "test.py")

    print("Hello from my-cursor!, location:", location)

    response = agent.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": f"Please fix the bugs in the test.py file present at {location}. For editing the file, you can use the same file location and name.",
                }
            ],
        }
    )

    for message in response["messages"]:
        print(message.content)


if __name__ == "__main__":
    main()
