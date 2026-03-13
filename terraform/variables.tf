variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "eu-north-1"
}

variable "project_name" {
  description = "Name of the project"
  type        = string
  default     = "qallm-mvp"
}

variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "openai_api_key" {
  description = "OpenAI API Key for LLM service"
  type        = string
  sensitive   = true
  default     = ""
}

variable "anthropic_api_key" {
  description = "Anthropic API Key for LLM service"
  type        = string
  sensitive   = true
  default     = ""
}

variable "ollama_base_url" {
  description = "Base URL for Ollama API"
  type        = string
  default     = ""
}

variable "github_username" {
  description = "GitHub username or organization for GHCR"
  type        = string
}
