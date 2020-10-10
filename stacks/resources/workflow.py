from aws_cdk import (
    core,
    aws_ecs as ecs,
    aws_ecr as ecr,
    aws_s3 as s3,
    aws_codebuild as codebuild,
    aws_codepipeline as codepipeline,
    aws_codepipeline_actions as actions,
)

def create_pipeline(
    scope: core.Construct,
    stack_name: str,
    ecr_repository: ecr.Repository,
    repo_name:str,
    repo_owner: str,
    repo_branch: str,
    artifact_bucket: str,
    app_service: ecs.FargateService,
    github_access_token: str,
    enable_deploy_approval: bool = False,
    worker_service: ecs.FargateService = None,
):

    project = codebuild.PipelineProject(
        scope, 'build',
        project_name=stack_name,
        description=f'Build project for {stack_name}. Managed by AWS CDK.',
        environment=codebuild.BuildEnvironment(
            privileged=True, build_image=codebuild.LinuxBuildImage.AMAZON_LINUX_2_2
        ),
        environment_variables={
            'REPOSITORY_URI': codebuild.BuildEnvironmentVariable(value=ecr_repository.repository_uri),
        },
        cache=codebuild.Cache.local(
            codebuild.LocalCacheMode.DOCKER_LAYER,
            codebuild.LocalCacheMode.CUSTOM,
            codebuild.LocalCacheMode.SOURCE
        ),
        build_spec=codebuild.BuildSpec.from_object({
            'version': '0.2',
            'phases': {
                'pre_build': {
                    'commands': [
                        '$(aws ecr get-login --no-include-email --region $AWS_REGION)',
                        'IMAGE_LATEST=${REPOSITORY_URI}:latest',
                        'IMAGE_VERSION=${REPOSITORY_URI}:${CODEBUILD_RESOLVED_SOURCE_VERSION:0:7}'
                    ]
                },
                'build': {
                    'commands': [
                        'docker build -f Dockerfile.prod -t ${IMAGE_LATEST} .',
                        'docker tag ${IMAGE_LATEST} ${IMAGE_VERSION}'
                    ]
                },
                'post_build': {
                    'commands': [
                        'docker push ${IMAGE_LATEST}',
                        'docker push ${IMAGE_VERSION}',
                        "printf '[{\"name\":\"container\",\"imageUri\":\"%s\"}]' ${IMAGE_VERSION} > imagedefinitions.json"
                    ]
                }
            },
            'artifacts': {
                'files': [
                    'imagedefinitions.json'
                ]
            }
        })
    )
    ecr_repository.grant_pull_push(project)
    source_output = codepipeline.Artifact()
    source_action = actions.GitHubSourceAction(
        action_name='Source',
        owner=repo_owner,
        repo=repo_name,
        branch=repo_branch,
        oauth_token=core.SecretValue.plain_text(github_access_token),
        output=source_output,
    )

    build_output = codepipeline.Artifact()
    build_action = actions.CodeBuildAction(
        action_name='Build',
        project=project,
        input=source_output,
        outputs=[build_output],
        type=actions.CodeBuildActionType.BUILD
    )

    artifact_bucket = s3.Bucket.from_bucket_name(scope, 'artifactBucket', artifact_bucket)

    deploy_actions = [
        actions.EcsDeployAction(
            action_name='App',
            service=app_service,
            input=build_output,
        )
    ]
    if worker_service:
        deploy_actions.append(
            actions.EcsDeployAction(
                action_name='Worker',
                service=worker_service,
                input=build_output,
            )
        )

    pipeline = codepipeline.Pipeline(
        scope, 'pipeline',
        pipeline_name=stack_name,
        restart_execution_on_update=True,
        artifact_bucket=artifact_bucket,
    )
    pipeline.add_stage(
        stage_name='Source',
        actions=[source_action],
    )
    pipeline.add_stage(
        stage_name='Build',
        actions=[build_action]
    )
    if enable_deploy_approval:
        pipeline.add_stage(
            stage_name='Approval',
            actions=[
                actions.ManualApprovalAction(
                    action_name='Approve',
                    notify_emails=[]
                )
            ]
        )
    pipeline.add_stage(
        stage_name='Deploy',
        actions=deploy_actions,
    )

