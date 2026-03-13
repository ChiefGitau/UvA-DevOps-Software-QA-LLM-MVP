output "alb_url" {
  description = "Access the website via this URL"
  value       = "http://${aws_lb.main.dns_name}"
}

# outputs

output "aws_region" {
  value = var.aws_region
}
