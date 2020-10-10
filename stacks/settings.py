import json
from typing import List

import environ

env = environ.Env()

AWS_ACCOUNT_ID = env.str('AWS_ACCOUNT_ID')
AWS_DEFAULT_REGION = env.str('AWS_DEFAULT_REGION')


class StackConfig(object):
    stack_name: str = None
    kms_key_uuid: str = None
    cache_node_type: str = None
    num_cache_nodes: int = None
    database_size: str = None
    database_name: str = None
    database_username: str = None
    database_allocated_storage: int = None
    database_encrypted: bool = False
    artifact_bucket: str = None
    certificate_key_id: str = None
    repo_owner: str = None
    repo_name: str = None
    repo_branch: str = None
    dns_name: str = None
    dns_zone_id: str = None  # Domain
    dns_stack_subdomain: str = None
    github_access_token: str = None
    enable_deploy_approval: bool = False

    def __init__(
        self,
        stack_name: str,
        kms_key_uuid: str,
        cache_node_type: str,
        num_cache_nodes: int,
        database_size: str,
        database_name: str,
        database_username: str,
        database_allocated_storage: int,
        database_encrypted: bool,
        artifact_bucket: str,
        certificate_key_id: str,
        repo_owner: str,
        repo_name: str,
        repo_branch: str,
        dns_name: str,
        dns_zone_id: str,
        dns_stack_subdomain: str,
        github_access_token: str,
        enable_deploy_approval: bool,
    ):
        self.stack_name = stack_name
        self.kms_key_uuid = kms_key_uuid
        self.cache_node_type = cache_node_type
        self.num_cache_nodes = num_cache_nodes
        self.database_size = database_size
        self.database_name = database_name
        self.database_username = database_username
        self.database_allocated_storage = database_allocated_storage
        self.database_encrypted = database_encrypted
        self.artifact_bucket = artifact_bucket
        self.certificate_key_id = certificate_key_id
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.repo_branch = repo_branch
        self.dns_name = dns_name
        self.dns_zone_id = dns_zone_id
        self.dns_stack_subdomain = dns_stack_subdomain
        self.github_access_token = github_access_token
        self.enable_deploy_approval = enable_deploy_approval

    @classmethod
    def get_configs(cls, config_file='./cdk.stacks.json') -> List["StackConfig"]:
        config = open(config_file, 'r')
        config_json = json.load(config)

        stack_configs = []
        for item in config_json:
            stack_configs.append(StackConfig(**item))
        return stack_configs
