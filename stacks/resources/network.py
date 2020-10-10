from aws_cdk import (
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_route53 as route53,
    aws_route53_targets as route53_targets,
    aws_elasticloadbalancingv2 as elbv2,
    core,
)


def retrieve_vpc(scope: core.Construct, vpc_name: str):
    return ec2.Vpc.from_lookup(scope, 'vpc', vpc_name=vpc_name)


def create_vpc(scope: core.Construct, vpc_name: str):
    return ec2.Vpc(
        scope,
        vpc_name,
        max_azs=2,
        cidr='10.10.0.0/16',
        # configuration will create 3 groups in 2 AZs = 6 subnets.
        subnet_configuration=[
            ec2.SubnetConfiguration(
                subnet_type=ec2.SubnetType.PUBLIC,
                name='Public',
                cidr_mask=23  # 512 ip addresses
            ), ec2.SubnetConfiguration(
                subnet_type=ec2.SubnetType.PRIVATE,
                name='Private',
                cidr_mask=23  # 512 ip addresses
            ), ec2.SubnetConfiguration(
                subnet_type=ec2.SubnetType.ISOLATED,
                name='Isolated',
                cidr_mask=24  # 256 ip addresses
            )
        ],
        nat_gateways=1,
    )


def create_load_balancer(scope: core.Construct, vpc: ec2.IVpc):
    return elbv2.ApplicationLoadBalancer(
        scope, 'loadBalancer',
        vpc=vpc,
        deletion_protection=False,
        http2_enabled=True,
        idle_timeout=core.Duration.seconds(60),
        internet_facing=True,
        vpc_subnets=ec2.SubnetSelection(
            subnet_type=ec2.SubnetType.PUBLIC
        ),
    )


def configure_load_balancing(
    load_balancer: elbv2.ApplicationLoadBalancer,
    ec2_service: ecs.FargateService,
    ssl_certificate=None,
):
    # Redirection 80 --> 443
    if ssl_certificate:
        redirect_listener = load_balancer.add_listener('redirect', port=80, open=True)
        redirect_listener.add_redirect_response('redirect', status_code='HTTP_301', protocol='HTTPS', port='443')

        https_listener = load_balancer.add_listener(
            'listener',
            port=443,
            certificates=[ssl_certificate],
            open=True
        )
        https_listener.add_targets(
            'target', port=80,
            deregistration_delay=core.Duration.seconds(30),
            slow_start=core.Duration.seconds(30),
            targets=[ec2_service],
            health_check=elbv2.HealthCheck(path='/')
        )
    else:
        http_listener = load_balancer.add_listener('listener', port=80, open=True)
        http_listener.add_targets(
            'target', port=80,
            deregistration_delay=core.Duration.seconds(30),
            slow_start=core.Duration.seconds(30),
            targets=[ec2_service],
            health_check=elbv2.HealthCheck(path='/')
        )


def configure_domain(
    scope: core.Construct,
    load_balancer: elbv2.ApplicationLoadBalancer,
    dns_name: str,
    dns_zone_id: str,
    dns_stack_subdomain: str,
):
    # // DNS record
    zone = route53.HostedZone.from_hosted_zone_attributes(
        scope, 'dns',
        zone_name=dns_name,
        hosted_zone_id=dns_zone_id,
    )
    target = route53.RecordTarget.from_alias(route53_targets.LoadBalancerTarget(load_balancer))
    route53.ARecord(scope, 'stack-domain', zone=zone, record_name=dns_stack_subdomain, target=target)

