from langchain_core.load import dumps, loads
import langchain
from langchain.chat_models import init_chat_model
from langchain.agents import create_agent

from read_tool import ReadAndWriteTool


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
    tools = [ReadAndWriteTool()]
    agent = create_agent(
        model=model,
        tools=tools,
        system_prompt=prompt,
    ).with_config({"recursion_limit": 20})

    print("Hello from my-cursor!")
    message = input("Enter your message: ")

    while message != "exit":
        response = agent.invoke(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": message,
                    }
                ],
            }
        )

        if message == "exit":
            print("Thank you for using my-cursor!")
            break

        for message in response["messages"]:
            print(message.content)

        message = input("Enter your message: ")
    # print(dumps(response, pretty=True))


if __name__ == "__main__":
    main()
