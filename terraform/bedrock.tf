locals {
    openapi_s3_bucket = "your-openapi-s3-bucket"
#     instruction       = <<EOF
#  You are an automated testing agent skilled at generating Pytest test cases for Django code changes.
#  When provided with a commit of file changes, your role is to: Analyze the modified code to understand the functionality and behavior. 
#  Generate relevant Pytest test cases to verify the new or updated logic. 
#  After that create a new unique branch in the same GitHub repository. Commit the generated test cases into that new branch. Open a pull request from the new branch to the base branch. To retrieve the content of any file. All operations must be performed sequentially to ensure: The branch is created before committing the test file. The test file is committed before creating the pull request. The pull request correctly references the branch where the test file was committed. Your final output should be a GitHub pull request containing the new Pytest test cases.
# EOF
    instruction= file("../bedrock_agent/agent-instructions.txt")
}

variable "openapi_s3_key" {
  description = "The S3 object key for the OpenAPI schema"
  type        = string
  default     = "openapi/openapi.yaml"
}

resource "aws_bedrockagent_agent" "qa_agent" {
  agent_name        = "my-qa-agent"
  instruction       = local.instruction
  foundation_model  = "anthropic.claude-3-haiku-20240307-v1:0"
  agent_resource_role_arn = aws_iam_role.bedrock_agent_role.arn
}

resource "aws_bedrockagent_agent_action_group" "qa_action_group" {
  agent_id           = aws_bedrockagent_agent.qa_agent.id
  action_group_name  = "my-action-group"
  action_group_state = "ENABLED"
  agent_version      = "DRAFT"
  skip_resource_in_use_check = true
  api_schema {
    # s3 {
    #   s3_bucket_name = aws_s3_bucket.openapi_bucket.id
    #   s3_object_key  = var.openapi_s3_key
    # }
    payload = file("../bedrock_agent/github_ag_openapi_schema.yaml")
  }
  action_group_executor {
    lambda = aws_lambda_function.github_action_group_lambda.arn
  }
}

resource "aws_bedrockagent_agent_alias" "qa_agent_alias" {
  agent_id = aws_bedrockagent_agent.qa_agent.id
  agent_alias_name = "my-qa-agent-alias-1"
  description = "Alias for my QA agent"
  depends_on = [ aws_bedrockagent_agent_action_group.qa_action_group ]
}

resource "aws_iam_role" "lambda_exec" {
  name = "lambda-execution-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Effect = "Allow",
      Principal = {
        Service = "lambda.amazonaws.com"
      },
      Action = "sts:AssumeRole"
    }]
  })
}


resource "aws_iam_role" "bedrock_agent_role" {
  name = "bedrock-agent-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Effect = "Allow",
      Principal = {
        Service = "bedrock.amazonaws.com"
      },
      Action = "sts:AssumeRole"
    }]
  })

}
  
resource "aws_iam_role_policy" "bedrock_agent_invoke_model" {
    name = "AmazonBedrockAgentBedrockFoundationModelPolicyProd"
    role = aws_iam_role.bedrock_agent_role.id
  
    policy = jsonencode({
      Version = "2012-10-17",
      Statement = [
        {
          Sid = "AmazonBedrockAgentBedrockFoundationModelPolicyProd",
          Effect = "Allow",
          Action = [
            "bedrock:InvokeModel",
            "bedrock:InvokeModelWithResponseStream"
          ],
          Resource = [
            "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-3-haiku-20240307-v1:0",
            "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-3-5-sonnet-20240620-v1:0"
          ]
        }
      ]
    })
  }

# resource "aws_iam_role_policy" "bedrock_agent_invoke_lambda" {
#   name = "allow-agent-invoke-models"
#   role = aws_iam_role.bedrock_agent_role.id

#   policy = jsonencode({
#     Version = "2012-10-17",
#     Statement = [{
#       Effect = "Allow",
#       Action = "lambda:InvokeFunction",
#       Resource = aws_lambda_function.github_action_group_lambda.arn
#     }]
#   })
# }

resource "aws_s3_bucket" "openapi_bucket" {
  bucket = local.openapi_s3_bucket
}

resource "aws_s3_object" "openapi_schema" {
    bucket = aws_s3_bucket.openapi_bucket.id
    key    = var.openapi_s3_key
    source = "../bedrock_agent/github_ag_openapi_schema.yaml"
    etag   = filemd5("../bedrock_agent/github_ag_openapi_schema.yaml")
}