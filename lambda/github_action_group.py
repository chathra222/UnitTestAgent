import json
import os
import base64
import urllib.request

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")

def get_param_from_request_body(event, key):
    try:
        content = event.get("requestBody", {}).get("content", {})
        json_content = content.get("application/json", {})
        properties = json_content.get("properties", [])

        for param in properties:
            if param.get("name") == key:
                return param.get("value")
    except Exception as e:
        print(f"Error extracting '{key}' from requestBody: {e}")

    return None

def extract_parameters(param_list):
    return {item['name']: item['value'] for item in param_list if 'name' in item and 'value' in item}

def format_bedrock_response(action_group, api_path, http_method, status_code, payload, message_version=1):
    return {
        "response": {
            "actionGroup": action_group,
            "apiPath": api_path,
            "httpMethod": http_method,
            "httpStatusCode": status_code,
            "responseBody": {
                "application/json": {
                    "body": payload
                }
            }
        },
        "messageVersion": message_version
    }

def lambda_handler(event, context):
    print(event)
    parameters = extract_parameters(event.get("parameters", []))
    action_group = event.get("actionGroup", "unknown")
    api_path = event.get("apiPath", "unknown")
    http_method = event.get("httpMethod", "unknown")
    message_version = event.get("messageVersion", 1)
    if parameters:
        print("parameters:", parameters)
        repo = parameters.get("repo")
        owner = parameters.get("owner")

    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "Bedrock-Agent"
    }

    # 1. GET /file-content
    print("api_path:", api_path)
    print("http_method:", http_method)
    if api_path == "/file-content" and http_method.upper() == "GET":
        filepath = parameters.get("filepath")
        branch = parameters.get("branch", "main")

        if not repo or not owner or not filepath:
            print("Missing 'repo', 'owner', or 'filepath'")
            return format_bedrock_response(action_group, api_path, http_method, 400, {"error": "Missing 'repo', 'owner', or 'filepath'"}, message_version)

        try:
            url = f"https://api.github.com/repos/{owner}/{repo}/contents/{filepath}?ref={branch}"
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req) as res:
                data = json.loads(res.read())
                content = base64.b64decode(data['content']).decode('utf-8')
            print("content:", content)

            return format_bedrock_response(action_group, api_path, http_method, 200, content, message_version)

        except Exception as e:
            print("Error:", e)
            return format_bedrock_response(action_group, api_path, http_method, 500, {"error": str(e)}, message_version)

    # 2. POST /create-branch
    elif api_path == "/create-branch" and http_method.upper() == "POST":
        print(event)
        action_group = event.get("actionGroup", "unknown")
        api_path = event.get("apiPath", "unknown")
        http_method = event.get("httpMethod", "unknown")
        message_version = event.get("messageVersion", 1)
        if parameters:
            base_branch = parameters.get("base")
            new_branch = parameters.get("new_branch")
        else:
            repo = get_param_from_request_body(event,"repo")
            owner = get_param_from_request_body(event,"owner")
            base_branch = get_param_from_request_body(event,"base")
            new_branch = get_param_from_request_body(event,"new_branch")
        print("base_branch:", base_branch)
        print("new_branch:", new_branch)
        print("repo:", repo)
        print("owner:", owner)
        if not repo or not owner or not base_branch or not new_branch:
            return format_bedrock_response(action_group, api_path, http_method, 400, {"error": "Missing 'repo', 'owner', 'base', or 'new_branch'"}, message_version)

        try:
            # Get SHA of base branch
            url = f"https://api.github.com/repos/{owner}/{repo}/git/ref/heads/{base_branch}"
            print("url:", url)
            req = urllib.request.Request(url, headers=headers)
            print("req:", req)
            with urllib.request.urlopen(req) as res:
                data = json.loads(res.read())
                sha = data['object']['sha']

            # Create new branch
            url = f"https://api.github.com/repos/{owner}/{repo}/git/refs"
            payload = {
                "ref": f"refs/heads/{new_branch}",
                "sha": sha
            }
            print("payload:", payload)
            req = urllib.request.Request(
                url,
                headers=headers,
                method="POST",
                data=json.dumps(payload).encode("utf-8")
            )
            print("req:", req)
            with urllib.request.urlopen(req) as res:
                result = json.loads(res.read())
                print("result:", result)

            return format_bedrock_response(action_group, api_path, http_method, 201, result, message_version)

        except Exception as e:
            print("Error:", e)
            return format_bedrock_response(action_group, api_path, http_method, 500, {"error": str(e)}, message_version)

    # 3. PUT /file
    elif api_path == "/file" and http_method.upper() == "PUT":
        print(event)
        if parameters:
            filepath = parameters.get("filepath")
            content = parameters.get("content")
            branch = parameters.get("branch", "main")
            commit_message = parameters.get("message", "Add file via Bedrock Agent")
        if not parameters:
            filepath = get_param_from_request_body(event,"filepath")
            repo = get_param_from_request_body(event, "repo")
            owner== get_param_from_request_body(event, "owner")
            content = get_param_from_request_body(event,"content")
            branch = get_param_from_request_body(event,"branch")
            commit_message = get_param_from_request_body(event,"message")
        print("filepath:", filepath)
        print("repo:", repo)
        print("owner:", owner)
        print("branch:", branch)
        print("commit_message:", commit_message)
        print("content:", content)
        if not repo or not owner or not filepath or not content:
            return format_bedrock_response(action_group, api_path, http_method, 400, {"error": "Missing 'repo', 'owner', 'filepath', or 'content'"}, message_version)

        try:
            # Check if file exists
            url = f"https://api.github.com/repos/{owner}/{repo}/contents/{filepath}?ref={branch}"
            req = urllib.request.Request(url, headers=headers)
            try:
                with urllib.request.urlopen(req) as res:
                    existing_data = json.loads(res.read())
                    sha = existing_data.get("sha")
            except:
                sha = None

            encoded_content = base64.b64encode(content.encode('utf-8')).decode()

            payload = {
                "message": commit_message,
                "content": encoded_content,
                "branch": branch
            }
            if sha:
                payload["sha"] = sha

            req = urllib.request.Request(
                url,
                method="PUT",
                headers=headers,
                data=json.dumps(payload).encode("utf-8")
            )
            with urllib.request.urlopen(req) as res:
                response_data = json.loads(res.read())

            return format_bedrock_response(action_group, api_path, http_method, 200, response_data, message_version)

        except Exception as e:
            print("Error:", e)
            return format_bedrock_response(action_group, api_path, http_method, 500, {"error": str(e)}, message_version)

    # 4. POST /create-pull-request
    elif api_path == "/create-pull-request" and http_method.upper() == "POST":
        if parameters:
            title = parameters.get("title")
            body = parameters.get("body", "")
            head = parameters.get("head", "main")
            base = parameters.get("base", "main")
        else:
            repo = get_param_from_request_body(event, "repo")
            owner = get_param_from_request_body(event, "owner")
            title = get_param_from_request_body(event,"title")
            body = get_param_from_request_body(event,"body")
            head = get_param_from_request_body(event,"head")
            base = get_param_from_request_body(event,"base")

        if not repo or not owner or not title:
            return format_bedrock_response(action_group, api_path, http_method, 400, {"error": "Missing 'repo', 'owner', or 'title'"}, message_version)

        try:
            url = f"https://api.github.com/repos/{owner}/{repo}/pulls"
            payload = {
                "title": title,
                "body": body,
                "head": head,
                "base": base
            }

            req = urllib.request.Request(url, method="POST", headers=headers, data=json.dumps(payload).encode('utf-8'))
            with urllib.request.urlopen(req) as res:
                response_data = json.loads(res.read())

            return format_bedrock_response(action_group, api_path, http_method, 201, response_data, message_version)

        except Exception as e:
            print("Error:", e)
            return format_bedrock_response(action_group, api_path, http_method, 500, {"error": str(e)}, message_version)

    # Unknown endpoint
    else:
        return format_bedrock_response(action_group, api_path, http_method, 404, {"error": "Unsupported endpoint or method"}, message_version)