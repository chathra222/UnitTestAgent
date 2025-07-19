🎯 Your Goal:
"A developer pushes code to GitHub. A Bedrock-powered agent is triggered, analyzes the code changes, reasons about what needs to be tested, generates pytest test cases, and autonomously opens a pull request."


[1] Developer Pushes Code to GitHub ✅
           ↓
[2] GitHub Webhook → API Gateway → Lambda 
           ↓
[3] Lambda filters the changes required unit tests
           ↓
[4] Lambda invokes the agent and commit info and relevant context (e.g., file paths, commit message) to Bedrock Agent(invoke_agent)
           ↓
[5] Bedrock Agent calls 
  - get_file_content - action group
           ↓
  - generate test cases
           ↓
  - creates a new branch
           ↓
  - commit the generated test cases
           ↓
  - create a pull request
           ↓
[7] GitHub CI/CD pipeline runs pytest on the new branch
           ↓
[8] Developer reviews and merges the PR



🧠 Why This Demo Is Agentic
✔️ Autonomy: no user prompt required
✔️ Tool use: GitHub APIs + Bedrock
✔️ Action loop: reason → generate → act → validate
✔️ Multi-modal: uses raw code + structured metadata


🎥 Demo Storyboard (Live or Slide)
Frame	                                       What You Show
👨‍💻 1. Dev commits to feature/register-user	git push origin feature/register-user
🔁 2. Webhook triggers your Lambda	         (show CloudWatch logs)
🧠 3. Lambda gets diff + symbols	         
🧠 4. Bedrock generates test	             show Claude test output
🧾 5. Lambda opens PR on GitHub	             auto-generated test file
🧪 6. CI runs pytest → green ✅	            test passes
✅ 7. Dev merges PR	                        done



🧱 Folder Structure (IaC + Code)

bedrock-auto-tester/
├── bedrock-agent/
│   ├── instructions.md               # Bedrock Agent prompt instructions
│   └── knowledge_base/               # Optional KB (e.g., testing patterns, sample test cases)
│       └── test_examples.txt
│
├── lambda/
│   ├── handler.py                    # Main Lambda function
│   ├── github_compare.py            # Logic to query GitHub Compare API
│   ├── bedrock_client.py            # Logic to call Bedrock Agent
│   ├── pr_creator.py                # GitHub PR creation logic
│   └── utils.py                     # Common utilities (e.g., token parsing, logging)
│
├── deployment/
│   ├── terraform/                    # Terraform for AWS infra (API Gateway, Lambda, IAM)
│   │   ├── main.tf
│   │   └── variables.tf
│   └── layer/                        # Optional Lambda layer for Python packages
│       └── python/
│           └── requirements.txt
│
├── test/
│   └── sample_code_push.json        # Sample GitHub webhook payload for local testing
│
├── .github/
│   └── workflows/
│       └── ci.yml                   # GitHub Actions pipeline to run pytest
│
├── README.md
└── requirements.txt                 # Python dependencies for local testing

