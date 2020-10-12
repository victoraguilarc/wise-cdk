
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

from stacks.settings import StackConfig


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
            resources=['*'],
            actions=['ecs:ListClusters', 'ecs:ListContainerInstances', 'ecs:DescribeContainerInstances']
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
            actions=['kms:ListKeys', 'kms:ListAliases', 'kms:Describe*', 'kms:Decrypt']
        )
    )
    policy.add_statements(
        iam.PolicyStatement(
            resources=[f'arn:aws:ssm:*:*:parameter/{stack_name}/*'],
            actions=['ssm:GetParameters', 'ssm:GetParametersByPath']
        )
    )

    return policy


def create_task_definition(
    scope: core.Construct,
    ecr_repository: ecr.Repository,
    log_group: logs.LogGroup,
    policy: iam.Policy,
    s3_bucket: s3.Bucket,
    stack_name: str,
    service_name: str,
    config: StackConfig,
    role: str = None,
    command: list = None,
):
    task_definition = ecs.FargateTaskDefinition(
        scope, f'TaskDefinition-{role}',
        cpu=512,
        memory_limit_mib=1024,
        family=service_name,
    )

    container_props = dict()
    if command:
        container_props['command'] = command

    app_container = task_definition.add_container(
        'container',
        image=ecs.ContainerImage.from_ecr_repository(ecr_repository),
        logging=ecs.LogDrivers.aws_logs(
            stream_prefix=service_name,
            log_group=log_group
        ),
        environment={
            'AWS_REGION': scope.region,
            'DD_ENV': config.stack_label,
            'DD_API_KEY': config.datadog_api_key,
            'DD_SERVICE': role,
            'DD_VERSION': '1',  # TODO calculate in the building
            'STACK_NAME': stack_name,
            'DD_APM_ENABLED': 'true',
            'DD_AGENT_HOST': '0.0.0.0',
            'DD_TRACE_AGENT_PORT': '8126',
        },
        **container_props,
    )
    app_container.add_port_mappings(ecs.PortMapping(container_port=8000))
    task_definition.task_role.attach_inline_policy(policy)

    #
    #  D A T A D O G
    #
    if config.datadog_api_key:
        datadog_container = task_definition.add_container(
            'datadog-agent',
            image=ecs.ContainerImage.from_registry('datadog/agent:latest'),
            memory_limit_mib=256,
            cpu=12,
            logging=ecs.LogDrivers.aws_logs(
                stream_prefix=stack_name,
                log_group=log_group
            ),
            environment={
                'AWS_REGION': scope.region,
                'DD_API_KEY': config.datadog_api_key,
                'DD_APM_ENABLED': 'true',
                'DD_APM_NON_LOCAL_TRAFFIC': 'true',
                'DD_APM_RECEIVER_PORT': '8126',
                'DD_DOGSTATSD_NON_LOCAL_TRAFFIC': 'true',
                'DD_DOGSTATSD_PORT': '8125',
                'ECS_FARGATE': 'true',
            },
        )
        datadog_container.add_port_mappings(
            ecs.PortMapping(container_port=8126, protocol=ecs.Protocol.TCP)
        )
        datadog_container.add_port_mappings(
            ecs.PortMapping(container_port=8125, protocol=ecs.Protocol.UDP)
        )

    task_definition.task_role.attach_inline_policy(policy)
    s3_bucket.grant_read_write(task_definition.task_role)
    return task_definition


def create_fargate_service(
    scope: core.Construct,
    service_name: str,
    ecs_cluster: ecs.Cluster,
    task_definition: ecs.TaskDefinition,
    desired_count: int,
    role: str,
    has_health_check: bool = False,
):

    service_props = dict()
    if has_health_check:
        service_props['health_check_grace_period'] = core.Duration.seconds(10)

    service = ecs.FargateService(
        scope, f'service-{role}',
        service_name=service_name,
        cluster=ecs_cluster,
        task_definition=task_definition,
        assign_public_ip=False,
        desired_count=desired_count,
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

