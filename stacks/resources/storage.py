
from aws_cdk import (
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_ecr as ecr,
    aws_rds as rds,
    aws_s3 as s3,
    aws_elasticache as elasticache,
    core,
)
from aws_cdk.aws_ec2 import IVpc
from aws_cdk.core import RemovalPolicy

from stacks.settings import StackConfig


def create_bucket(scope: core.Construct, stack_name: str):
    return s3.Bucket(
        scope, 'bucket',
        bucket_name=stack_name,
        public_read_access=True,
        removal_policy=RemovalPolicy.DESTROY,
    )


def create_redis_cache(scope: core.Construct, stack_name: str, vpc: IVpc, config: StackConfig):
    subnet_ids = vpc.select_subnets(subnet_type=ec2.SubnetType.PRIVATE).subnet_ids

    cache_subnet_group = elasticache.CfnSubnetGroup(
        scope, 'cacheSubnetGroup',
        cache_subnet_group_name=f'{stack_name}-redis',
        description=stack_name,
        subnet_ids=subnet_ids,
    )
    cache_security_group = ec2.SecurityGroup(
        scope, 'cacheSecurityGroup',
        vpc=vpc,
        allow_all_outbound=True,
        security_group_name=f'{stack_name}-redis',
        description=stack_name,
    )
    cache = elasticache.CfnCacheCluster(
        scope, 'elasticache',
        cluster_name=stack_name,
        engine='redis', port=6379,
        cache_node_type=config.cache_node_type,
        num_cache_nodes=config.num_cache_nodes,
        cache_subnet_group_name=cache_subnet_group.cache_subnet_group_name,
        vpc_security_group_ids=[cache_security_group.security_group_id],
    )

    cache_security_group.add_ingress_rule(
        ec2.Peer.any_ipv4(), ec2.Port.tcp(6379), 'Allow Cache Access'
    )

    core.CfnOutput(
        scope=scope,
        id='redisAddress',
        value=cache.attr_redis_endpoint_address
    )

    return cache


def create_rds_cluster(
    scope: core.Construct,
    stack_name: str, vpc: IVpc,
    database_name: str,
    database_username: str,
    datbase_password: str,
    database_encrypted: bool
):
    subnet_ids = []
    for subnet in vpc.private_subnets:
        subnet_ids.append(subnet.subnet_id)

    db_subnet_group = rds.CfnDBSubnetGroup(
        scope=scope,
        id='dbSubnetGroup',
        db_subnet_group_description='Subnet group to access RDS',
        db_subnet_group_name=stack_name,
        subnet_ids=subnet_ids,
    )

    db_scurity_group = ec2.SecurityGroup(
        scope=scope,
        id='dbSecurityGroup',
        vpc=vpc,
        allow_all_outbound=True,
        description=stack_name,
    )
    db_scurity_group.add_ingress_rule(ec2.Peer.any_ipv4(), ec2.Port.tcp(5432))

    database = rds.CfnDBCluster(
        scope=scope,
        id='database',
        database_name=database_name,
        db_cluster_identifier=stack_name,
        engine=rds.DatabaseInstanceEngine.POSTGRES,
        engine_mode='serverless',
        master_username=database_username,
        master_user_password=core.SecretValue.plain_text(datbase_password).to_string(),
        port=5432,
        db_subnet_group_name=db_subnet_group.db_subnet_group_name,
        vpc_security_group_ids=[db_scurity_group.security_group_id],
        storage_encrypted=database_encrypted,
        scaling_configuration=rds.CfnDBCluster.ScalingConfigurationProperty(
            auto_pause=True,
            max_capacity=2,
            min_capacity=1,
            seconds_until_auto_pause=3600,
        )
    )
    database.add_depends_on(db_subnet_group)

    return database


def create_rds_instance(
    scope: core.Construct,
    stack_name: str,
    vpc: IVpc,
    config: StackConfig,
    ecs_cluster: ecs.Cluster,
):
    database = rds.DatabaseInstance(
        scope, f'{stack_name}-rds',
        vpc=vpc,
        engine=rds.DatabaseInstanceEngine.postgres(
            version=rds.PostgresEngineVersion.VER_11
        ),
        port=5432,
        credentials=rds.Credentials.from_username(config.database_username),
        instance_identifier=stack_name,
        instance_type=ec2.InstanceType(config.database_size),
        database_name=config.database_name,
        allocated_storage=config.database_allocated_storage,
        multi_az=False,
        allow_major_version_upgrade=False,
        delete_automated_backups=True,
        deletion_protection=False,
        auto_minor_version_upgrade=False,
        backup_retention=core.Duration.days(5),
        enable_performance_insights=True,
        storage_encrypted=config.database_encrypted,

        vpc_placement=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC),
    )

    core.CfnOutput(
        scope=scope,
        id='rdsAddress',
        value=database.db_instance_endpoint_address
    )

    return database


def create_ecr_repository(scope: core.Construct, stack_name: str):
    return ecr.Repository(
        scope, 'ecr',
        lifecycle_rules=[
            ecr.LifecycleRule(max_image_age=core.Duration.days(30))
        ],
        removal_policy=core.RemovalPolicy.DESTROY,
        repository_name=stack_name,
    )
