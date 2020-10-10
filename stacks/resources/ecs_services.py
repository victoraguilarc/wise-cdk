
from aws_cdk import (
    aws_ecs as ecs,
    aws_ec2 as ec2,
    aws_ecr as ecr,
    aws_iam as iam,
    aws_s3 as s3,
    aws_logs as logs,
    core,
)
from aws_cdk.aws_ec2 import IVpc


def create_cluster(scope: core.Construct, stack_name: str, vpc: IVpc):
    return ecs.Cluster(
        scope, 'cluster',
        cluster_name=stack_name,
        vpc=vpc,
        container_insights=True,
    )


def create_services_policy(scope: core.Construct, stack_name: str, kms_key: str):
    policy = iam.Policy(scope, 'policy', policy_name=stack_name)
    parameter_key_arn = scope.format_arn(service='kms', resource='key', resource_name=kms_key)

    policy.add_statements(
        iam.PolicyStatement(
            resources=['*'],
            actions=['ssm:GetParameters', 'ssm:GetParametersByPath']
        )
    )
    policy.add_statements(
        iam.PolicyStatement(
            resources=['arn:aws:ssm:*:*:*'],
            actions=['ssm:DescribeParameters']
        )
    )
    policy.add_statements(
        iam.PolicyStatement(
            resources=[parameter_key_arn],
            actions=[
                'kms:ListKeys',
                'kms:ListAliases',
                'kms:Describe*',
                'kms:Decrypt',
            ]
        )
    )
    policy.add_statements(
        iam.PolicyStatement(
            resources=[f'arn:aws:ssm:*:*:parameter/{stack_name}/*'],
            actions=['ssm:GetParameters', 'ssm:GetParametersByPath']
        )
    )

    return policy


def get_service_name(stack_name: str, role: str = None):
    role_id = f'-{role}' if role else ''
    return f'{stack_name}{role_id}', role_id


def create_task_definition(
    scope: core.Construct,
    ecr_repository: ecr.Repository,
    log_group: logs.LogGroup,
    policy: iam.Policy,
    s3_bucket: s3.Bucket,
    stack_name: str,
    role: str = None,
    command: list = None,
):
    service_name, role_id = get_service_name(stack_name, role)

    task_definition = ecs.FargateTaskDefinition(
        scope, f'TaskDefinition{role_id}',
        cpu=512,
        memory_limit_mib=1024,
        family=service_name,
    )
    container_props = {
        'image': ecs.ContainerImage.from_ecr_repository(ecr_repository),
        'logging': ecs.LogDrivers.aws_logs(
            stream_prefix=stack_name,
            log_group=log_group
        ),
        'environment': {
            'STACK_NAME': stack_name,
            'STACK_SERVICE_NAME': service_name,
            'AWS_REGION': scope.region,
        }
    }
    if command:
        container_props['command'] = command

    task_definition.add_container(
        f'container{role_id}',
        **container_props,
    ).add_port_mappings(ecs.PortMapping(container_port=8000))
    task_definition.task_role.attach_inline_policy(policy)

    s3_bucket.grant_read_write(task_definition.task_role)

    return task_definition


def create_fargate_service(
    scope: core.Construct,
    stack_name: str,
    ecs_cluster: ecs.Cluster,
    task_definition: ecs.TaskDefinition,
    has_health_check: bool = False,
    role: str = None,
):
    service_name, role_id = get_service_name(stack_name, role)

    service_props = dict()
    if has_health_check:
        service_props['health_check_grace_period'] = core.Duration.seconds(10)

    service = ecs.FargateService(
        scope, f'service{role_id}',
        service_name=service_name,
        cluster=ecs_cluster,
        task_definition=task_definition,
        assign_public_ip=False,
        desired_count=1,
        max_healthy_percent=100,
        min_healthy_percent=0,
        vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE),
        **service_props,
    )
    scaling = service.auto_scale_task_count(
        max_capacity=5
    )
    scaling.scale_on_cpu_utilization(
        'CpuScaling',
        target_utilization_percent=50,
        scale_in_cooldown=core.Duration.seconds(60),
        scale_out_cooldown=core.Duration.seconds(60),
    )
    return service

