import os
import base64
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers.string import StrOutputParser

def format_data_for_openai(diffs, readme_content, commit_messages):
    prompt = None

    # Combine the changes into a string with clear delineation.
    changes = '\n'.join([f"File: {diff['filename']}\nDiff: \n{diff['patch']}" for diff in diffs])

    # Combine all commit messages
    commit_messages = '\n'.join(commit_messages) + '\n\n'

    # Decode the README content
    readme_content = base64.b64decode(readme_content.content).decode('utf-8')

    # Construct the prompt with clear instructions for the LLM.
    prompt = (
        "Please review the following code changes and commit messages from a GitHub pull request:\n"
        "Code changes from Pull Request:\n"
        f"{changes}\n"
        "Commit messages:\n"
        f"{commit_messages}"
        "Here is the current README file content:\n"
        f"{readme_content}\n"
        "Consider the code changes and commit messages, determine if the README needs to be updated. If so, edit the README, ensuring to maintain its existing style and clarity.\n"
        "Updated README:\n"
    )

    return prompt

def call_openai(prompt):
    client = ChatOpenAI(api_key=os.environ['OPENAI_API_KEY'], model="gpt-3.5-turbo-0125")

    try:
        messages = [
            {
                "role": "system",
                "content": "You are an AI trained to help with updating README files based on code changes and commit messages."
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
        response = client.invoke(input=messages)
        # We use the StrOutputParser to parse the response as this class can adapt to providers like OpenAI, Llama and others.
        parser = StrOutputParser()
        content = parser.invoke(input=response)
        return content
    except Exception as e:
        print(f"Error calling OpenAI: {e}")

def update_readme_and_create_pr(repo, updated_readme, readme_sha):
    commit_messages = "AI COMMIT: Proposed README update based on code changes"
    commit_sha = os.getenv('COMMIT_SHA')
    main_brainch = repo.get_branch("main")
    new_branch_name = f'update-readme-{commit_sha[:7]}'
    new_branch = repo.create_git_ref(ref=f"refs/heads/{new_branch_name}", sha=main_brainch.commit.sha)

    repo.update_file(
        path="README.md",
        message=commit_messages,
        content=updated_readme,
        sha=readme_sha,
        branch=new_branch_name
    )

    pr_title = "AI PR: Update README based on recent changes"
    pr_body = "This is an AI PR. Please review the README."
    pull_request = repo.create_pull(title=pr_title, body=pr_body, head=new_branch_name, base="main")

    return pull_request