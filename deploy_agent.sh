cd lambda
zip webhook_handler.zip webhook_handler.py
zip github_action_group.zip github_action_group.py
cd ../terraform
terraform init
terraform apply -auto-approve