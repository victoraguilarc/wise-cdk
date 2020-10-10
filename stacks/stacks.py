
from aws_cdk import (
    aws_ec2 as ec2,
    aws_certificatemanager as certificate_manager,
    core,
)

from stacks.resources.ecs_services import (
    create_cluster,
    create_services_policy,
    create_task_definition,
    create_fargate_service,
)
from stacks.resources.monitoring import create_log_group
from stacks.resources.network import (
    create_vpc,
    create_load_balancer,
    configure_load_balancing,
    configure_domain,
)
from stacks.resources.storage import (
    create_bucket,
    create_redis_cache,
    create_rds_instance,
    create_ecr_repository,
)
from stacks.resources.workflow import create_pipeline
from stacks.settings import StackConfig


class VPCStack(core.Stack):
    vpc_name: str = None
    vpc: ec2.IVpc = None

    def __init__(self, scope: core.Construct, id: str, vpc_name: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        self.vpc_name = vpc_name
        self.synth()

    def synth(self):
        self.vpc = create_vpc(self, self.vpc_name)

    def get_vpc(self):
        return self.vpc


class PlatformStack(core.Stack):
    def __init__(self, scope: core.Construct, id: str, vpc: ec2.IVpc, config: StackConfig = None, **kwargs):
        super().__init__(scope, id, **kwargs)

        self.vpc = vpc
        self.config = config
        self.synth()

    def synth(self):
        #  1.  ECS : Cluster
        ecs_cluster = create_cluster(self, self.stack_name, self.vpc)

        #  2.  S3 - BUCKET
        s3_bucket = create_bucket(self, self.stack_name)

        #  3.  LOGGING
        log_group = create_log_group(self, self.stack_name)

        #  4.  IAM  POLICY  FOR  SECRETS
        policy = create_services_policy(self, self.stack_name, self.config.kms_key_uuid)

        #  5.  REDIS CACHE
        cache = create_redis_cache(
            scope=self,
            stack_name=self.stack_name,
            vpc=self.vpc,
            cache_node_type=self.config.cache_node_type,
            num_cache_nodes=self.config.num_cache_nodes,
        )

        #  6.  DATABASE
        database = create_rds_instance(
            scope=self,
            stack_name=self.stack_name,
            vpc=self.vpc,
            database_name=self.config.database_name,
            database_username=self.config.database_username,
            database_size=self.config.database_size,
            database_allocated_storage=self.config.database_allocated_storage,
            database_encrypted=self.config.database_encrypted,
            ecs_cluster=ecs_cluster,
        )

        #  7.  ECR
        ecr_repository = create_ecr_repository(self, self.stack_name)

        #  8.  TASK DEFINITIONS: app / worker
        app_task_definition = create_task_definition(
            scope=self,
            stack_name=self.stack_name,
            ecr_repository=ecr_repository,
            log_group=log_group,
            policy=policy,
            s3_bucket=s3_bucket,
        )
        worker_task_definition = create_task_definition(
            scope=self,
            stack_name=self.stack_name,
            ecr_repository=ecr_repository,
            log_group=log_group,
            policy=policy,
            s3_bucket=s3_bucket,
            role='worker',
            command=['/worker']
        )

        #  9.  ECS : Services
        app_service = create_fargate_service(
            scope=self,
            stack_name=self.stack_name,
            ecs_cluster=ecs_cluster,
            task_definition=app_task_definition,
            has_health_check=True,
        )
        worker_service = create_fargate_service(
            scope=self,
            stack_name=self.stack_name,
            ecs_cluster=ecs_cluster,
            task_definition=worker_task_definition,
            has_health_check=False,
            role='worker',
        )

        database.connections.allow_default_port_from(ecs_cluster)
        database.connections.allow_from(app_service, port_range=ec2.Port.tcp(5432))
        database.connections.allow_from(worker_service, port_range=ec2.Port.tcp(5432))
        database.secret.grant_read(app_task_definition.obtain_execution_role())
        database.secret.grant_read(worker_task_definition.obtain_execution_role())

        s3_bucket.grant_public_access()

        #  10.  LOAD BALANCER / app only
        certificate_key = self.format_arn(
            service='acm',
            resource='certificate',
            resource_name=self.config.certificate_key_id,
        )
        certificate = certificate_manager.Certificate.from_certificate_arn(
            self, 'certificate', certificate_key
        )
        load_balancer = create_load_balancer(self, self.vpc)
        configure_load_balancing(load_balancer, app_service, ssl_certificate=certificate)

        #  11.  DNS RECORD
        configure_domain(
            scope=self,
            load_balancer=load_balancer,
            dns_name=self.config.dns_name,
            dns_zone_id=self.config.dns_zone_id,
            dns_stack_subdomain=self.config.dns_stack_subdomain,
        )

        #  12.  BUILD PIPELINE
        pipeline = create_pipeline(
            self,
            stack_name=self.stack_name,
            ecr_repository=ecr_repository,
            repo_name=self.config.repo_name,
            repo_owner=self.config.repo_owner,
            repo_branch=self.config.repo_branch,
            artifact_bucket=self.config.artifact_bucket,
            app_service=app_service,
            github_access_token=self.config.github_access_token,
            worker_service=None,
            enable_deploy_approval=self.config.enable_deploy_approval,
        )

