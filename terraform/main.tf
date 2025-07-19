provider "aws" {
  region = "us-east-1"
}

resource "aws_iam_role" "lambda_exec_role" {
  name = "lambda_exec_role"

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

resource "aws_iam_role_policy_attachment" "lambda_basic_execution" {
  role       = aws_iam_role.lambda_exec_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# This policy allows the Lambda function to access the Bedrock Agent Runtime
resource "aws_iam_role_policy_attachment" "bedrock_agent_runtime" {
  role       = aws_iam_role.lambda_exec_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonBedrockFullAccess"
}

resource "aws_lambda_function" "webhook_handler_lambda" {
  function_name    = "webhook_handlerLambda"
  role             = aws_iam_role.lambda_exec_role.arn
  runtime          = "python3.11"
  handler          = "webhook_handler.lambda_handler"
  filename         = "../lambda/webhook_handler.zip"
  source_code_hash = filebase64sha256("../lambda/webhook_handler.zip")
  layers           = [aws_lambda_layer_version.requests_layer.arn]
  timeout          = 900
  environment {
    variables = {
      GITHUB_TOKEN = var.github_token
      AGENT_ID    = aws_bedrockagent_agent.qa_agent.id
      ALIAS_ID    = aws_bedrockagent_agent_alias.qa_agent_alias.agent_alias_id
    }
  }
}


resource "aws_lambda_function" "github_action_group_lambda" {
  function_name    = "github_action_groupLambda"
  role             = aws_iam_role.lambda_exec_role.arn
  runtime          = "python3.11"
  handler          = "github_action_group.lambda_handler"
  filename         = "../lambda/github_action_group.zip"
  source_code_hash = filebase64sha256("../lambda/github_action_group.zip")
  layers           = [aws_lambda_layer_version.requests_layer.arn]
  timeout          = 900
  environment {
    variables = {
      GITHUB_TOKEN = var.github_token
    }
  }
}

resource "aws_apigatewayv2_api" "api" {
  name          = "webhook_handler-api"
  protocol_type = "HTTP"
}

resource "aws_apigatewayv2_integration" "lambda_integration" {
  api_id           = aws_apigatewayv2_api.api.id
  integration_type = "AWS_PROXY"
  integration_uri  = aws_lambda_function.webhook_handler_lambda.invoke_arn
  integration_method = "POST"
  payload_format_version = "2.0"
}

resource "aws_lambda_layer_version" "requests_layer" {
  filename   = "../lambda/layer/requests-layer.zip"
  layer_name = "requests"
  compatible_runtimes = ["python3.11"]
  source_code_hash = filebase64sha256("../lambda/layer/requests-layer.zip")
}

resource "aws_apigatewayv2_route" "default_route" {
  api_id    = aws_apigatewayv2_api.api.id
  route_key = "POST /webhook"
  target    = "integrations/${aws_apigatewayv2_integration.lambda_integration.id}"
}

resource "aws_apigatewayv2_integration" "github_action_group_integration" {
  api_id           = aws_apigatewayv2_api.api.id
  integration_type = "AWS_PROXY"
  integration_uri  = aws_lambda_function.github_action_group_lambda.invoke_arn
  integration_method = "POST"
  payload_format_version = "2.0"
}
resource "aws_apigatewayv2_route" "file_content_route" {
  api_id    = aws_apigatewayv2_api.api.id
  route_key = "GET /file_content"
  target    = "integrations/${aws_apigatewayv2_integration.github_action_group_integration.id}"
}
resource "aws_apigatewayv2_route" "create_pull_request_route" {
  api_id    = aws_apigatewayv2_api.api.id
  route_key = "GET /create-pull-request"
  target    = "integrations/${aws_apigatewayv2_integration.github_action_group_integration.id}"
}
resource "aws_apigatewayv2_route" "commit_file_route" {
  api_id    = aws_apigatewayv2_api.api.id
  route_key = "PUT /file"
  target    = "integrations/${aws_apigatewayv2_integration.github_action_group_integration.id}"
}
resource "aws_apigatewayv2_route" "create_branch_route" {
  api_id    = aws_apigatewayv2_api.api.id
  route_key = "POST /create-branch"
  target    = "integrations/${aws_apigatewayv2_integration.github_action_group_integration.id}"
}


resource "aws_apigatewayv2_stage" "default_stage" {
  api_id      = aws_apigatewayv2_api.api.id
  name        = "$default"
  auto_deploy = true
}

resource "aws_lambda_permission" "apigw_invoke_webhook_handlers" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.webhook_handler_lambda.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.api.execution_arn}/*/*"
}


resource "aws_lambda_permission" "apigw_invoke_github_action_group" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.github_action_group_lambda.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.api.execution_arn}/*/*"
}


resource "aws_lambda_permission" "bedrock_agent_invoke_github_action_groups" {
  statement_id  = "AllowBedrockAgentInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.github_action_group_lambda.function_name  # Update to your actual Lambda resource

  principal     = "bedrock.amazonaws.com"
  source_arn    = aws_bedrockagent_agent.qa_agent.agent_arn  # Update to your actual Bedrock Agent ARN
  #source_arn    = "arn:aws:bedrock:us-east-1:469795145196:agent/WBOOFOERXI"  # Update to your actual API Gateway ARN
  # Optional: restrict based on Bedrock Agent ARN
}