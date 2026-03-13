resource "aws_efs_file_system" "shared_data" {
  creation_token = "${var.project_name}-data"
  encrypted      = true
  tags           = { Name = "${var.project_name}-efs" }
}

resource "aws_efs_mount_target" "main" {
  count           = 2
  file_system_id  = aws_efs_file_system.shared_data.id
  subnet_id       = aws_subnet.public[count.index].id
  security_groups = [aws_security_group.efs.id]
}

resource "aws_efs_access_point" "main" {
  file_system_id = aws_efs_file_system.shared_data.id
  posix_user {
    gid = 1000
    uid = 1000
  }
  root_directory {
    path = "/data"
    creation_info {
      owner_gid   = 1000
      owner_uid   = 1000
      permissions = "777"
    }
  }
}
