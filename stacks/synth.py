from aws_cdk import core

from stacks.settings import StackConfig
from stacks.stacks import PlatformStack, VPCStack
from stacks import settings


def synth_stacks(app):
    aws_account = core.Environment(
        account=settings.AWS_ACCOUNT_ID,
        region=settings.AWS_DEFAULT_REGION,
    )

    for config in StackConfig.get_configs():
        vpc_stack = VPCStack(
            scope=app,
            id=f'{config.stack_name}-vpc',
            vpc_name=config.stack_name,
            env=aws_account,
        )

        PlatformStack(
            scope=app,
            id=config.stack_name,
            vpc=vpc_stack.get_vpc(),
            config=config,
            env=aws_account,
        )
