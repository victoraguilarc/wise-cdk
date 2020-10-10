from aws_cdk import (
    aws_logs as logs,
    core,
)


def create_log_group(scope: core.Construct, stack_name: str):
    return logs.LogGroup(
        scope, 'logGroup',
        retention=logs.RetentionDays.ONE_WEEK,
        log_group_name=stack_name,
    )
