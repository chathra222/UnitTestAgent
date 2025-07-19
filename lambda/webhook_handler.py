import json
#import requests
import boto3
import logging
import os
from botocore.exceptions import ClientError
import logging
from typing import Dict, Any
# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

#import environment variables
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
AGENT_ID = os.environ.get("AGENT_ID")
ALIAS_ID = os.environ.get("ALIAS_ID")

print(f"The agent id is {AGENT_ID}")
print(f"The alias id is {ALIAS_ID}")
def invoke_agent(client, agent_id, alias_id, prompt, session_id):
        response = client.invoke_agent(
            agentId=agent_id,
            agentAliasId=alias_id,
            enableTrace=True,
            sessionId = session_id,
            inputText=prompt,
            streamingConfigurations = { 
    "applyGuardrailInterval" : 20,
      "streamFinalResponse" : False
            }
        )
        completion = ""
        print(f"The response is {response}")
        for event in response.get("completion"):
            #Collect agent output.
            if 'chunk' in event:
                chunk = event["chunk"]
                completion += chunk["bytes"].decode()
            
            # Log trace output.
            if 'trace' in event:
                trace_event = event.get("trace")
                trace = trace_event['trace']
                for key, value in trace.items():
                    logging.info("%s: %s",key,value)
                    print(f"printing trace output: {key}: {value}")

        print(f"Agent response: {completion}")

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    logger.info("Received event: %s", json.dumps(event))
    print(f"The event received is {event}")
    print(f"The event body received is {event['body']}")
    # Process the event from GitHub webhook
    # 1. Parse the webhook payload
    payload = json.loads(event["body"])
    #Get the ref
    ref = payload.get("ref", "")
    #only process if its push to feature branch
    if not ref.startswith("refs/heads/feature/"):
        print("Ignoring event as it is not a push to a feature branch")
        return {"statusCode": 200, "body": json.dumps({"message": "Not a feature branch push"})} 
    else:
        logger.info(f"Processing event for feature branch: {ref}")
        # 2. Collect all changed files
        changed_files = set()
        for commit in payload["commits"]:
            changed_files.update(commit.get("added", []))
            changed_files.update(commit.get("modified", []))
            changed_files.update(commit.get("removed", []))
        
        commit_info = json.dumps(payload["commits"], indent=2)
        # 3. Decide if test cases are needed
        def needs_tests(file):
            skip_patterns = ["README", ".md", ".json", "migrations/", "tests/"]
            return not any(pattern in file for pattern in skip_patterns)

        files_requiring_tests = [f for f in changed_files if needs_tests(f)]

        print("Files that may need new/updated tests:", files_requiring_tests)

        client = boto3.client(service_name="bedrock-agent-runtime")

        agent_id = AGENT_ID
        alias_id = ALIAS_ID
        session_id = "my_session-id"
        prompt = f"""
            You must execute below tasks in order 

            1. Create a branch
                - Branch naming convention should follow 
                - unit-tests/<source-branch-name>-<short-commit-hash>
                Example: unit-tests/feature-add-user-abc1234 

            2. Generate high quality unit test cases using pytest framework for Django application
                - Only generate for these modified files: {', '.join(files_requiring_tests)}
                - Use the commit context provided below to guide the test coverage:{commit_info}

            3. Commit the generated test files to this new branch
                - Its path should be under the tests/ directory of the Django app.
            
            4. Create pull request with proper details  

            MUST FOLLOW INSTRUCTIONS: 
            - Must commit all changes to the branch before raising a PR request 
            - Ensure the generated tests follow best practices for maintainability and readability.
            - Aim for meaningful coverage of all logic and edge cases introduced in the code changes.
        """
        print(f"The prompt is {prompt}")
        try:

            invoke_agent(client, agent_id, alias_id, prompt, session_id)
        
        except ClientError as e:
            print(f"Client error: {str(e)}")
            logger.error("Client error: %s", {str(e)})
        return {"statusCode": 200, "body": json.dumps(event)}