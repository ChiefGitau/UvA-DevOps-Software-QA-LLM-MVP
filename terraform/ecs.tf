resource "aws_ecs_cluster" "main" {
  name = "${var.project_name}-cluster"
}

# Service Discovery Namespace
resource "aws_service_discovery_private_dns_namespace" "main" {
  name        = "svc"
  description = "Service discovery for p4 qallm"
  vpc         = aws_vpc.main.id
}

# CloudWatch Logs
resource "aws_cloudwatch_log_group" "ecs" {
  name              = "/ecs/${var.project_name}"
  retention_in_days = 7
}

# --- Service: Session ---
resource "aws_service_discovery_service" "session" {
  name = "session-service"
  dns_config {
    namespace_id = aws_service_discovery_private_dns_namespace.main.id
    dns_records {
      ttl  = 10
      type = "A"
    }
  }
}

resource "aws_ecs_task_definition" "session" {
  family                   = "${var.project_name}-session"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "256"
  memory                   = "512"
  execution_role_arn       = aws_iam_role.ecs_task_execution_role.arn
  task_role_arn            = aws_iam_role.ecs_task_role.arn

  container_definitions = jsonencode([{
    name  = "session-service"
    image = "ghcr.io/${lower(var.github_username)}/uva-devops-software-qa-llm-mvp-session:latest"
    portMappings = [{ containerPort = 8000 }]
    environment = [
      { name = "DATA_DIR", value = "/app/data" }
    ]
    mountPoints = [{
      containerPath = "/app/data"
      sourceVolume  = "app-data"
      readOnly      = false
    }]
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.ecs.id
        "awslogs-region"        = var.aws_region
        "awslogs-stream-prefix" = "session"
      }
    }
  }])

  volume {
    name = "app-data"
    efs_volume_configuration {
      file_system_id     = aws_efs_file_system.shared_data.id
      transit_encryption = "ENABLED"
      authorization_config {
        access_point_id = aws_efs_access_point.main.id
        iam             = "ENABLED"
      }
    }
  }
}

resource "aws_ecs_service" "session" {
  name            = "session-service"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.session.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = aws_subnet.public[*].id
    security_groups  = [aws_security_group.ecs.id]
    assign_public_ip = true
  }

  service_registries {
    registry_arn = aws_service_discovery_service.session.arn
  }
}

# --- Repeat for Analysis ---
resource "aws_service_discovery_service" "analysis" {
  name = "analysis-service"
  dns_config {
    namespace_id = aws_service_discovery_private_dns_namespace.main.id
    dns_records {
      ttl  = 10
      type = "A"
    }
  }
}

resource "aws_ecs_task_definition" "analysis" {
  family                   = "${var.project_name}-analysis"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "512" # Higher CPU for analysis tools
  memory                   = "1024"
  execution_role_arn       = aws_iam_role.ecs_task_execution_role.arn
  task_role_arn            = aws_iam_role.ecs_task_role.arn

  container_definitions = jsonencode([{
    name  = "analysis-service"
    image = "ghcr.io/${lower(var.github_username)}/uva-devops-software-qa-llm-mvp-analysis:latest"
    portMappings = [{ containerPort = 8000 }]
    environment = [
      { name = "DATA_DIR", value = "/app/data" }
    ]
    mountPoints = [{
      containerPath = "/app/data"
      sourceVolume  = "app-data"
      readOnly      = false
    }]
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.ecs.id
        "awslogs-region"        = var.aws_region
        "awslogs-stream-prefix" = "analysis"
      }
    }
  }])

  volume {
    name = "app-data"
    efs_volume_configuration {
      file_system_id     = aws_efs_file_system.shared_data.id
      transit_encryption = "ENABLED"
      authorization_config {
        access_point_id = aws_efs_access_point.main.id
        iam             = "ENABLED"
      }
    }
  }
}

resource "aws_ecs_service" "analysis" {
  name            = "analysis-service"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.analysis.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = aws_subnet.public[*].id
    security_groups  = [aws_security_group.ecs.id]
    assign_public_ip = true
  }

  service_registries {
    registry_arn = aws_service_discovery_service.analysis.arn
  }
}

# --- Repeat for LLM ---
resource "aws_service_discovery_service" "llm" {
  name = "llm-service"
  dns_config {
    namespace_id = aws_service_discovery_private_dns_namespace.main.id
    dns_records {
      ttl  = 10
      type = "A"
    }
  }
}

resource "aws_ecs_task_definition" "llm" {
  family                   = "${var.project_name}-llm"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "256"
  memory                   = "512"
  execution_role_arn       = aws_iam_role.ecs_task_execution_role.arn
  task_role_arn            = aws_iam_role.ecs_task_role.arn

  container_definitions = jsonencode([{
    name  = "llm-service"
    image = "ghcr.io/${lower(var.github_username)}/uva-devops-software-qa-llm-mvp-llm:latest"
    portMappings = [{ containerPort = 8000 }]
    environment = [
      { name = "DATA_DIR", value = "/app/data" },
      { name = "OPENAI_API_KEY", value = var.openai_api_key },
      { name = "ANTHROPIC_API_KEY", value = var.anthropic_api_key },
      { name = "OLLAMA_BASE_URL", value = var.ollama_base_url }
    ]
    mountPoints = [{
      containerPath = "/app/data"
      sourceVolume  = "app-data"
      readOnly      = false
    }]
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.ecs.id
        "awslogs-region"        = var.aws_region
        "awslogs-stream-prefix" = "llm"
      }
    }
  }])

  volume {
    name = "app-data"
    efs_volume_configuration {
      file_system_id     = aws_efs_file_system.shared_data.id
      transit_encryption = "ENABLED"
      authorization_config {
        access_point_id = aws_efs_access_point.main.id
        iam             = "ENABLED"
      }
    }
  }
}

resource "aws_ecs_service" "llm" {
  name            = "llm-service"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.llm.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = aws_subnet.public[*].id
    security_groups  = [aws_security_group.ecs.id]
    assign_public_ip = true
  }

  service_registries {
    registry_arn = aws_service_discovery_service.llm.arn
  }
}

# --- Service: Frontend ---
resource "aws_ecs_task_definition" "frontend" {
  family                   = "${var.project_name}-frontend"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "256"
  memory                   = "512"
  execution_role_arn       = aws_iam_role.ecs_task_execution_role.arn

  container_definitions = jsonencode([{
    name  = "frontend"
    image = "ghcr.io/${lower(var.github_username)}/uva-devops-software-qa-llm-mvp-frontend:latest"
    portMappings = [{ containerPort = 80 }]
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.ecs.id
        "awslogs-region"        = var.aws_region
        "awslogs-stream-prefix" = "frontend"
      }
    }
  }])
}

resource "aws_ecs_service" "frontend" {
  name            = "frontend"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.frontend.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = aws_subnet.public[*].id
    security_groups  = [aws_security_group.ecs.id]
    assign_public_ip = true
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.frontend.arn
    container_name   = "frontend"
    container_port   = 80
  }
}
